"""Evidence-gated bridge from repeated execution gaps to capability acquisition.

This module does not create or execute capabilities. It detects repeated,
verified capability gaps, produces a bounded acquisition proposal, and leaves
practice, validation, safety review, and graduation to CapabilityAcquirer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .capability_acquisition import CapabilityAcquirer, CapabilityNeed, CapabilityProposal


@dataclass(frozen=True)
class CapabilityGap:
    task_family: str
    capability: str
    failure_count: int
    evidence_ids: tuple[str, ...]
    verified: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityEvolutionDecision:
    status: str
    gap: CapabilityGap
    proposal: CapabilityProposal | None
    reasons: tuple[str, ...] = ()


class CapabilityEvolution:
    """Detect repeated capability gaps and gate acquisition proposals."""

    def __init__(
        self,
        acquirer: CapabilityAcquirer,
        *,
        min_failures: int = 3,
        min_independent_evidence: int = 3,
    ) -> None:
        if not isinstance(acquirer, CapabilityAcquirer):
            raise TypeError("acquirer must be CapabilityAcquirer")
        if min_failures < 2:
            raise ValueError("min_failures must be at least 2")
        if min_independent_evidence < 2:
            raise ValueError("min_independent_evidence must be at least 2")
        self.acquirer = acquirer
        self.min_failures = min_failures
        self.min_independent_evidence = min_independent_evidence

    def detect(
        self,
        task_family: str,
        capability: str,
        experiences: Iterable[Mapping[str, object]],
    ) -> CapabilityGap:
        if not isinstance(task_family, str) or not task_family.strip():
            raise ValueError("task_family is required")
        if not isinstance(capability, str) or not capability.strip():
            raise ValueError("capability is required")

        failures = 0
        evidence: set[str] = set()
        verified_failures = 0

        for experience in experiences:
            outcome = str(experience.get("outcome", "")).strip().lower()
            if outcome not in {"failed", "regressed"}:
                continue
            failures += 1
            ids = experience.get("evidence_ids", ())
            if isinstance(ids, str):
                ids = (ids,)
            evidence.update(str(item).strip() for item in ids if str(item).strip())
            if bool(experience.get("verified", False)):
                verified_failures += 1

        reasons: list[str] = []
        if failures < self.min_failures:
            reasons.append("insufficient repeated failures")
        if verified_failures < self.min_failures:
            reasons.append("insufficient verified failures")
        if len(evidence) < self.min_independent_evidence:
            reasons.append("insufficient independent evidence")

        return CapabilityGap(
            task_family.strip(),
            capability.strip(),
            failures,
            tuple(sorted(evidence)),
            not reasons,
            tuple(reasons),
        )

    def evaluate(
        self,
        task_family: str,
        capability: str,
        experiences: Iterable[Mapping[str, object]],
    ) -> CapabilityEvolutionDecision:
        gap = self.detect(task_family, capability, experiences)
        if not gap.verified:
            return CapabilityEvolutionDecision("observe", gap, None, gap.reasons)

        proposal = self.acquirer.propose(
            CapabilityNeed(
                gap.task_family,
                gap.capability,
                gap.failure_count,
                gap.evidence_ids,
                True,
            )
        )
        if proposal is None:
            return CapabilityEvolutionDecision(
                "observe",
                gap,
                None,
                ("acquisition gate rejected the detected gap",),
            )
        return CapabilityEvolutionDecision(
            "propose",
            gap,
            proposal,
            ("repeated verified gap crossed acquisition threshold",),
        )


__all__ = ["CapabilityEvolution", "CapabilityEvolutionDecision", "CapabilityGap"]
