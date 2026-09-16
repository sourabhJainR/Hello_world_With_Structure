"""Bounded execution and learning loop for active information gathering."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable
from uuid import uuid4

from .information_planner import InformationAction, InformationPlanner
from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class InformationExecution:
    uncertainty_after: float
    evidence_ids: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class InformationReceipt:
    execution_id: str
    action_id: str
    uncertainty_before: float
    uncertainty_after: float
    expected_gain: float
    realized_gain: float
    evidence_ids: tuple[str, ...]
    verified: bool
    error: str | None = None
    created_at: str = ""


class ActiveInformationLoop:
    """Select, execute, measure, and persist a bounded information probe."""

    def __init__(self, memory: PersistentMemory, project: str, *, planner: InformationPlanner | None = None,
                 max_executions: int = 100_000) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if max_executions < 1:
            raise ValueError("max_executions must be positive")
        self.memory = memory
        self.project = project.strip()
        self.planner = planner or InformationPlanner()
        self.max_executions = max_executions
        with self.memory._lock, self.memory._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS active_information_executions(
                project TEXT NOT NULL, execution_id TEXT NOT NULL, action_id TEXT NOT NULL,
                uncertainty_before REAL NOT NULL, uncertainty_after REAL NOT NULL,
                expected_gain REAL NOT NULL, realized_gain REAL NOT NULL, evidence_ids TEXT NOT NULL,
                verified INTEGER NOT NULL, error TEXT, created_at TEXT NOT NULL,
                PRIMARY KEY(project, execution_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_active_information_action ON active_information_executions(project, action_id, created_at)")

    def execute(self, *, uncertainty: float, actions: tuple[InformationAction, ...],
                probe: Callable[[InformationAction], InformationExecution], max_risk: float = 1.0) -> InformationReceipt:
        if not 0 <= uncertainty <= 1:
            raise ValueError("uncertainty must be between 0 and 1")
        plan = self.planner.choose(uncertainty=uncertainty, actions=actions, max_risk=max_risk)
        if plan is None:
            raise ValueError("no eligible information action")
        selected = next(action for action in actions if action.action_id == plan.action_id)
        execution_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        error: str | None = None
        evidence: tuple[str, ...] = ()
        realized = 0.0
        after = uncertainty
        verified = False
        try:
            result = probe(selected)
            if not isinstance(result, InformationExecution):
                raise TypeError("probe must return InformationExecution")
            if not 0 <= result.uncertainty_after <= 1:
                raise ValueError("probe uncertainty_after must be between 0 and 1")
            if result.uncertainty_after > uncertainty:
                raise ValueError("probe cannot report uncertainty higher than before-state")
            evidence = tuple(sorted(set(item.strip() for item in result.evidence_ids if isinstance(item, str) and item.strip())))
            realized = uncertainty - result.uncertainty_after
            after = result.uncertainty_after
            verified = bool(evidence)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:512]
        with self.memory._lock, self.memory._connect() as db:
            count = db.execute("SELECT COUNT(*) FROM active_information_executions WHERE project=?", (self.project,)).fetchone()[0]
            if count >= self.max_executions:
                raise ValueError("active information execution budget exceeded")
            db.execute(
                "INSERT INTO active_information_executions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (self.project, execution_id, selected.action_id, uncertainty, after, selected.expected_gain,
                 realized, json.dumps(evidence), int(verified), error, now),
            )
        return InformationReceipt(execution_id, selected.action_id, uncertainty, after, selected.expected_gain,
                                  realized, evidence, verified, error, now)


__all__ = ["ActiveInformationLoop", "InformationExecution", "InformationReceipt"]
