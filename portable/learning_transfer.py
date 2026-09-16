"""Evidence-gated learning transfer and durable memory consolidation.

The module reuses the canonical PersistentMemory SQLite database. Learning is
stored as structured experience, while consolidation writes only verified,
independently reproduced patterns back into normal project memory.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class LearningExperience:
    id: str
    source_project: str
    task_family: str
    capability: str
    outcome: str
    detail: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    verified: bool = False


@dataclass(frozen=True)
class TransferCandidate:
    detail: str
    capability: str
    task_family: str
    source_projects: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class ConsolidationReceipt:
    task_family: str
    capability: str
    detail: str
    source_projects: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    memory_id: str


def _clean(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must not be empty")
    return value


class LearningTransfer:
    """Record, transfer, and consolidate verified experience across projects."""

    def __init__(self, memory: PersistentMemory, target_project: str) -> None:
        self.memory = memory
        self.target_project = _clean(target_project, "target_project")
        with self.memory._lock, self.memory._connect() as db:  # same canonical store
            db.execute("""CREATE TABLE IF NOT EXISTS learning_experiences(
                id TEXT PRIMARY KEY,
                source_project TEXT NOT NULL,
                task_family TEXT NOT NULL,
                capability TEXT NOT NULL,
                outcome TEXT NOT NULL,
                detail TEXT NOT NULL,
                evidence_ids TEXT NOT NULL,
                confidence REAL NOT NULL,
                verified INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_learning_lookup
                ON learning_experiences(task_family, capability, verified, outcome)""")

    def record(self, experience: LearningExperience) -> None:
        if not isinstance(experience, LearningExperience):
            raise ValueError("experience must be a LearningExperience")
        for value, field in (
            (experience.id, "id"), (experience.source_project, "source_project"),
            (experience.task_family, "task_family"), (experience.capability, "capability"),
            (experience.outcome, "outcome"), (experience.detail, "detail"),
        ):
            _clean(value, field)
        if not 0 <= experience.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        evidence = tuple(sorted({_clean(item, "evidence_id") for item in experience.evidence_ids}))
        if experience.verified and not evidence:
            raise ValueError("verified learning requires evidence_ids")
        created_at = datetime.now(timezone.utc).isoformat()
        with self.memory._lock, self.memory._connect() as db:
            existing = db.execute("SELECT source_project,task_family,capability,outcome,detail,evidence_ids,confidence,verified FROM learning_experiences WHERE id=?", (experience.id,)).fetchone()
            if existing:
                incoming = (experience.source_project, experience.task_family, experience.capability, experience.outcome,
                            experience.detail, json.dumps(evidence), experience.confidence, int(experience.verified))
                if existing != incoming:
                    raise ValueError(f"learning experience id already exists with different content: {experience.id}")
                return
            db.execute("INSERT INTO learning_experiences VALUES(?,?,?,?,?,?,?,?,?,?)", (
                experience.id, experience.source_project, experience.task_family, experience.capability,
                experience.outcome, experience.detail, json.dumps(evidence), experience.confidence,
                int(experience.verified), created_at,
            ))

    def transfer(self, task_family: str, capability: str, *, limit: int = 10) -> list[TransferCandidate]:
        task_family = _clean(task_family, "task_family")
        capability = _clean(capability, "capability")
        if limit < 1:
            raise ValueError("limit must be positive")
        with self.memory._lock, self.memory._connect() as db:
            rows = db.execute("""SELECT detail,source_project,evidence_ids,confidence
                FROM learning_experiences
                WHERE task_family=? AND capability=? AND outcome='worked' AND verified=1
                  AND source_project<>?
                ORDER BY confidence DESC, created_at DESC, id""", (task_family, capability, self.target_project)).fetchall()
        groups: dict[str, dict[str, object]] = {}
        for detail, source_project, evidence_json, confidence in rows:
            item = groups.setdefault(str(detail), {"projects": set(), "evidence": set(), "confidence": 0.0})
            item["projects"].add(str(source_project))  # type: ignore[union-attr]
            item["evidence"].update(json.loads(evidence_json or "[]"))  # type: ignore[union-attr]
            item["confidence"] = max(float(item["confidence"]), float(confidence))
        candidates = [
            TransferCandidate(detail, capability, task_family, tuple(sorted(item["projects"])),
                              tuple(sorted(item["evidence"])), float(item["confidence"]))
            for detail, item in groups.items()
        ]
        return sorted(candidates, key=lambda x: (-len(x.source_projects), -x.confidence, x.detail))[:limit]

    def consolidate(self, task_family: str, capability: str, *, min_projects: int = 2) -> ConsolidationReceipt | None:
        task_family = _clean(task_family, "task_family")
        capability = _clean(capability, "capability")
        if min_projects < 2:
            raise ValueError("min_projects must be at least 2")
        candidates = self.transfer(task_family, capability, limit=100)
        candidates = [candidate for candidate in candidates if len(candidate.source_projects) >= min_projects]
        if not candidates:
            return None
        candidate = candidates[0]
        text = (
            f"Transferable pattern for {task_family}/{capability}: {candidate.detail}. "
            f"Independently reproduced across {len(candidate.source_projects)} projects."
        )
        record = self.memory.remember(
            self.target_project, "procedural_learning", text,
            confidence=candidate.confidence, verified=True, approved=True,
        )
        if record is None:
            return None
        return ConsolidationReceipt(task_family, capability, candidate.detail,
                                    candidate.source_projects, candidate.evidence_ids, record.id)


__all__ = ["ConsolidationReceipt", "LearningExperience", "LearningTransfer", "TransferCandidate"]
