"""Requirement contract extraction and validation for autonomous engineering."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    statement: str
    acceptance_criteria: tuple[str, ...]
    priority: str = "must"
    source: str = "user"

@dataclass(frozen=True)
class RequirementContract:
    intent: str
    requirements: tuple[Requirement, ...]
    ambiguities: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return bool(self.intent.strip()) and bool(self.requirements) and all(r.acceptance_criteria for r in self.requirements)

class RequirementContractEngine:
    """Build explicit, testable requirements without inventing missing facts."""

    def build(self, intent: str, requirements: Sequence[Requirement], *, ambiguities: Sequence[str] = (), assumptions: Sequence[str] = ()) -> RequirementContract:
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent is required")
        items = tuple(requirements)
        if not items:
            raise ValueError("at least one requirement is required")
        ids = [r.requirement_id.strip() for r in items]
        if any(not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("requirement IDs must be non-empty and unique")
        for r in items:
            if not r.statement.strip() or not r.acceptance_criteria:
                raise ValueError("every requirement needs a statement and acceptance criteria")
            if r.priority not in {"must", "should", "could"}:
                raise ValueError("invalid priority")
        return RequirementContract(intent.strip(), items, tuple(ambiguities), tuple(assumptions))

    def validate(self, contract: RequirementContract) -> tuple[str, ...]:
        issues=[]
        if not contract.complete: issues.append("requirement contract is incomplete")
        for r in contract.requirements:
            if not r.acceptance_criteria: issues.append(f"{r.requirement_id}: missing acceptance criteria")
        if contract.ambiguities: issues.append("unresolved ambiguities remain")
        return tuple(issues)

__all__=["Requirement","RequirementContract","RequirementContractEngine"]
