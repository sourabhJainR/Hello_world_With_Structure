"""Empirical self-model for AER capability calibration.

The self-model describes observed performance, not subjective model claims. It
uses recorded outcomes to estimate capability reliability and uncertainty. It
never grants permissions or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class CapabilityProfile:
    capability: str
    successes: int
    failures: int
    confidence: float
    observations: int


class SelfModel:
    """Persist bounded empirical capability outcomes and calibrated profiles."""

    def __init__(self, memory: PersistentMemory, project: str, *, max_outcomes: int = 100_000) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if max_outcomes < 1:
            raise ValueError("max_outcomes must be positive")
        self.memory = memory
        self.project = project
        self.max_outcomes = max_outcomes
        with sqlite3.connect(memory.path, timeout=10) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS self_model_outcomes(
                project TEXT NOT NULL, outcome_id TEXT NOT NULL, capability TEXT NOT NULL,
                success INTEGER NOT NULL, PRIMARY KEY(project, outcome_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_self_model_capability ON self_model_outcomes(project, capability, success, outcome_id)")

    def record(self, outcome_id: str, capability: str, *, success: bool) -> None:
        if not isinstance(outcome_id, str) or not outcome_id.strip() or not isinstance(capability, str) or not capability.strip():
            raise ValueError("outcome_id and capability are required")
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT capability,success FROM self_model_outcomes WHERE project=? AND outcome_id=?", (self.project, outcome_id)).fetchone()
            expected = (capability, int(success))
            if existing:
                if existing != expected:
                    raise ValueError("outcome_id already exists with different content")
                return
            count = db.execute("SELECT COUNT(*) FROM self_model_outcomes WHERE project=?", (self.project,)).fetchone()[0]
            if count >= self.max_outcomes:
                raise ValueError("self-model outcome budget exceeded")
            db.execute("INSERT INTO self_model_outcomes VALUES(?,?,?,?)", (self.project, outcome_id, capability, int(success)))

    def profile(self, capability: str) -> CapabilityProfile:
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability is required")
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            row = db.execute("SELECT SUM(success),SUM(CASE WHEN success=0 THEN 1 ELSE 0 END),COUNT(*) FROM self_model_outcomes WHERE project=? AND capability=?", (self.project, capability)).fetchone()
        successes = int(row[0] or 0)
        failures = int(row[1] or 0)
        observations = int(row[2] or 0)
        confidence = successes / observations if observations else 0.0
        return CapabilityProfile(capability, successes, failures, round(confidence, 6), observations)

    def should_escalate(self, capability: str, *, min_observations: int = 5, min_confidence: float = 0.8) -> bool:
        if min_observations < 1 or not 0 <= min_confidence <= 1:
            raise ValueError("escalation thresholds are invalid")
        profile = self.profile(capability)
        return profile.observations < min_observations or profile.confidence < min_confidence


__all__ = ["CapabilityProfile", "SelfModel"]
