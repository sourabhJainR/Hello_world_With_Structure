"""Proposal-only capability acquisition with evidence and safety gates."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class CapabilityNeed:
    task_family: str
    capability: str
    missing_count: int
    evidence_ids: tuple[str, ...]
    verified: bool

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in (self.task_family, self.capability)):
            raise ValueError("task_family and capability must be non-empty")
        if self.missing_count < 1:
            raise ValueError("missing_count must be positive")
        if any(not isinstance(value, str) or not value.strip() for value in self.evidence_ids):
            raise ValueError("evidence_ids must contain non-empty strings")


@dataclass(frozen=True)
class CapabilityProposal:
    id: str
    task_family: str
    capability: str
    missing_count: int
    evidence_ids: tuple[str, ...]
    executable: bool = False


@dataclass(frozen=True)
class ValidationEvidence:
    evidence_ids: tuple[str, ...]
    tests_passed: bool
    safety_reviewed: bool
    approved: bool = False


@dataclass(frozen=True)
class ValidationReceipt:
    proposal_id: str
    accepted: bool
    executable: bool
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class CapabilityAcquirer:
    """Turn repeated verified gaps into validated, but non-executable, proposals."""

    def __init__(self, memory: PersistentMemory, project: str, *, min_missing: int = 3) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if min_missing < 2:
            raise ValueError("min_missing must be at least 2")
        self.memory = memory
        self.project = project.strip()
        self.min_missing = min_missing
        with self.memory._lock, self.memory._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS capability_proposals(
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                task_family TEXT NOT NULL,
                capability TEXT NOT NULL,
                missing_count INTEGER NOT NULL,
                evidence_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")

    def propose(self, need: CapabilityNeed) -> CapabilityProposal | None:
        if not need.verified or need.missing_count < self.min_missing or len(need.evidence_ids) < self.min_missing:
            return None
        evidence = tuple(sorted(set(need.evidence_ids)))
        payload = f"{self.project}|{need.task_family.strip()}|{need.capability.strip()}|{need.missing_count}|{json.dumps(evidence)}"
        proposal_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        proposal = CapabilityProposal(proposal_id, need.task_family.strip(), need.capability.strip(), need.missing_count, evidence)
        with self.memory._lock, self.memory._connect() as db:
            db.execute("INSERT OR IGNORE INTO capability_proposals VALUES(?,?,?,?,?,?,?)",
                       (proposal.id, self.project, proposal.task_family, proposal.capability, proposal.missing_count,
                        json.dumps(proposal.evidence_ids), datetime.now(timezone.utc).isoformat()))
        return proposal

    def validate(self, proposal_id: str, evidence: ValidationEvidence) -> ValidationReceipt:
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise ValueError("proposal_id is required")
        if any(not isinstance(value, str) or not value.strip() for value in evidence.evidence_ids):
            raise ValueError("validation evidence must contain non-empty ids")
        with self.memory._lock, self.memory._connect() as db:
            row = db.execute("SELECT id,evidence_ids FROM capability_proposals WHERE id=? AND project=?", (proposal_id, self.project)).fetchone()
        if row is None:
            raise KeyError(f"unknown capability proposal: {proposal_id}")
        reasons: list[str] = []
        if not evidence.evidence_ids:
            reasons.append("missing validation evidence")
        if not evidence.tests_passed:
            reasons.append("validation tests did not pass")
        if not evidence.safety_reviewed:
            reasons.append("safety review is missing")
        if self.memory.require_approval and not evidence.approved:
            reasons.append("approval is required")
        accepted = not reasons
        return ValidationReceipt(proposal_id, accepted, False, tuple(sorted(set(evidence.evidence_ids))), tuple(reasons))


__all__ = ["CapabilityAcquirer", "CapabilityNeed", "CapabilityProposal", "ValidationEvidence", "ValidationReceipt"]
