"""Canonical execution envelope shared by planning, execution, and evidence.

The envelope is provider-neutral and serializable. It carries the identity and
freshness boundaries that must survive handoffs and state-graph execution
without becoming a second source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping


@dataclass(frozen=True)
class RepositoryReference:
    digest: str
    root: str = ""
    model: str = "portable.agency_codebase_context.CodebaseIndex"

    def __post_init__(self) -> None:
        if not self.digest:
            raise ValueError("repository digest is required")


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    snapshot: str = ""
    freshness: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")


@dataclass(frozen=True)
class ExecutionIntent:
    task_id: str
    goal: str
    non_goals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.task_id or not self.goal:
            raise ValueError("task_id and goal are required")


@dataclass(frozen=True)
class ExecutionPlanRef:
    plan_id: str
    task_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.plan_id:
            raise ValueError("plan_id is required")


@dataclass(frozen=True)
class ExecutionEnvelope:
    """Canonical evidence-carrying contract for one engineering execution."""

    intent: ExecutionIntent
    repository: RepositoryReference
    plan: ExecutionPlanRef
    evidence: tuple[EvidenceReference, ...] = ()
    decisions: tuple[str, ...] = ()
    changeset_id: str = ""
    verification_ids: tuple[str, ...] = ()
    review_ids: tuple[str, ...] = ()
    regression_ids: tuple[str, ...] = ()
    release_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError(f"unsupported execution envelope schema: {self.schema_version}")
        if self.intent.task_id not in self.plan.task_ids and self.plan.task_ids:
            raise ValueError("plan/task identity mismatch")
        seen: set[str] = set()
        for evidence in self.evidence:
            if evidence.evidence_id in seen:
                raise ValueError(f"duplicate evidence id: {evidence.evidence_id}")
            seen.add(evidence.evidence_id)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "intent": {
                "task_id": self.intent.task_id,
                "goal": self.intent.goal,
                "non_goals": list(self.intent.non_goals),
            },
            "repository": {
                "digest": self.repository.digest,
                "root": self.repository.root,
                "model": self.repository.model,
            },
            "plan": {
                "plan_id": self.plan.plan_id,
                "task_ids": list(self.plan.task_ids),
            },
            "evidence": [
                {"evidence_id": item.evidence_id, "snapshot": item.snapshot, "freshness": item.freshness}
                for item in self.evidence
            ],
            "decisions": list(self.decisions),
            "changeset_id": self.changeset_id,
            "verification_ids": list(self.verification_ids),
            "review_ids": list(self.review_ids),
            "regression_ids": list(self.regression_ids),
            "release_ids": list(self.release_ids),
            "metadata": dict(self.metadata),
        }

    def canonical_bytes(self) -> bytes:
        return (json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExecutionEnvelope":
        intent = raw.get("intent", {})
        repository = raw.get("repository", {})
        plan = raw.get("plan", {})
        envelope = cls(
            intent=ExecutionIntent(
                task_id=str(intent.get("task_id", "")),
                goal=str(intent.get("goal", "")),
                non_goals=tuple(intent.get("non_goals", ())),
            ),
            repository=RepositoryReference(**repository),
            plan=ExecutionPlanRef(
                plan_id=str(plan.get("plan_id", "")),
                task_ids=tuple(plan.get("task_ids", ())),
            ),
            evidence=tuple(EvidenceReference(**item) for item in raw.get("evidence", ())),
            decisions=tuple(raw.get("decisions", ())),
            changeset_id=str(raw.get("changeset_id", "")),
            verification_ids=tuple(raw.get("verification_ids", ())),
            review_ids=tuple(raw.get("review_ids", ())),
            regression_ids=tuple(raw.get("regression_ids", ())),
            release_ids=tuple(raw.get("release_ids", ())),
            metadata=dict(raw.get("metadata", {})),
            schema_version=str(raw.get("schema_version", "1.0")),
        )
        envelope.validate()
        return envelope


__all__ = [
    "EvidenceReference",
    "ExecutionEnvelope",
    "ExecutionIntent",
    "ExecutionPlanRef",
    "RepositoryReference",
]
