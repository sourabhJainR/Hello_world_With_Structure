"""Belief-aware planning context and durable post-action learning signals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Iterable, Mapping
from uuid import uuid4

from .self_model import SelfModel


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BeliefContext:
    belief_id: str
    statement: str
    confidence: float
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.belief_id, str) or not self.belief_id.strip():
            raise ValueError("belief_id must be non-empty")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("statement must be non-empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        evidence = tuple(sorted(set(item.strip() for item in self.evidence_ids if isinstance(item, str) and item.strip())))
        object.__setattr__(self, "evidence_ids", evidence)


@dataclass(frozen=True)
class LearningSignal:
    signal_id: str
    task_id: str
    intent: str
    status: str
    capability: str | None
    evidence: tuple[str, ...]
    digest: str
    created_at: str
    persistence_errors: tuple[str, ...] = ()


class CognitiveLearningLoop:
    """Project-scoped belief context and post-action learning adapter."""

    def __init__(self, memory, project: str, *, self_model: SelfModel | None = None, max_signals: int = 100_000) -> None:
        if not project or not project.strip():
            raise ValueError("project is required")
        if max_signals < 1:
            raise ValueError("max_signals must be positive")
        self.memory = memory
        self.project = project.strip()
        self.self_model = self_model or SelfModel(memory, self.project)
        self.max_signals = max_signals
        with self.memory._lock, self.memory._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cognitive_learning_signals(
                project TEXT NOT NULL, signal_id TEXT NOT NULL, task_id TEXT NOT NULL,
                intent TEXT NOT NULL, status TEXT NOT NULL, capability TEXT,
                evidence TEXT NOT NULL, digest TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(project, signal_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_cognitive_learning_task ON cognitive_learning_signals(project, task_id, created_at)")

    @staticmethod
    def select_beliefs(beliefs: Iterable[BeliefContext], *, limit: int = 8) -> tuple[BeliefContext, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        normalized = list(beliefs)
        return tuple(sorted(normalized, key=lambda item: (item.confidence, item.belief_id))[:limit])

    def record(self, *, task_id: str, intent: str, status: str, capability: str | None = None,
               evidence: Iterable[str] = (), context: str | None = None) -> LearningSignal:
        if not task_id.strip() or not intent.strip() or not status.strip():
            raise ValueError("task_id, intent and status are required")
        clean_evidence = tuple(sorted(set(item.strip() for item in evidence if isinstance(item, str) and item.strip())))
        signal_id = uuid4().hex
        payload = {"task_id": task_id, "intent": intent, "status": status, "capability": capability, "evidence": clean_evidence, "context": context}
        digest = _digest(payload)
        persistence_errors: list[str] = []
        try:
            with self.memory._lock, self.memory._connect() as db:
                count = db.execute("SELECT COUNT(*) FROM cognitive_learning_signals WHERE project=?", (self.project,)).fetchone()[0]
                if count >= self.max_signals:
                    raise ValueError("cognitive learning signal budget exceeded")
                db.execute(
                    "INSERT INTO cognitive_learning_signals VALUES(?,?,?,?,?,?,?,?,?)",
                    (self.project, signal_id, task_id, intent, status, capability, json.dumps(clean_evidence), digest, _utc()),
                )
            if capability:
                self.self_model.record(signal_id, capability, success=status in {"accepted", "completed", "success"}, context=context)
        except Exception as exc:
            persistence_errors.append(f"{type(exc).__name__}: {exc}")
        return LearningSignal(signal_id, task_id, intent, status, capability, clean_evidence, digest, _utc(), tuple(persistence_errors))


__all__ = ["BeliefContext", "CognitiveLearningLoop", "LearningSignal"]
