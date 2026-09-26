"""Autonomous capability invention with unseen-holdout and safety-gated graduation.

The engine proposes bounded recombinations of existing capabilities, evaluates
those compositions on holdouts that were not used to trigger the invention,
compares them with the incumbent pathway, and graduates only a verified
improvement that survives regression and safety gates.

Proposals are data only. This module never mutates execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from statistics import mean
from typing import Callable, Iterable, Mapping, Sequence

from .continual_learning import BenchmarkObservation, ContinualLearningGuard
from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class CapabilityComposition:
    id: str
    capabilities: tuple[str, ...]
    strategy: str
    resource_lane: str
    verification_depth: str


@dataclass(frozen=True)
class HoldoutResult:
    holdout_id: str
    candidate_score: float
    incumbent_score: float
    verified: bool
    safety_passed: bool
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.holdout_id.strip():
            raise ValueError("holdout_id is required")
        for name, value in (("candidate_score", self.candidate_score), ("incumbent_score", self.incumbent_score)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.verified and not self.evidence_ids:
            raise ValueError("verified holdout results require evidence_ids")


@dataclass(frozen=True)
class SafetyResult:
    passed: bool
    evidence_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class InventionCandidate:
    composition: CapabilityComposition
    holdouts: tuple[HoldoutResult, ...]
    candidate_score: float
    incumbent_score: float
    improvement: float
    regression_passed: bool
    safety_passed: bool
    verified: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class InventionReceipt:
    status: str
    problem: str
    incumbent: CapabilityComposition
    selected: InventionCandidate | None
    candidates: tuple[InventionCandidate, ...]
    reasons: tuple[str, ...] = ()
    graduated: bool = False


class AutonomousCapabilityInvention:
    """Bounded search over capability compositions with hard promotion gates."""

    def __init__(
        self,
        memory: PersistentMemory,
        project: str,
        *,
        max_candidates: int = 12,
        min_holdouts: int = 3,
        minimum_improvement: float = 0.02,
        regression_tolerance: float = 0.02,
    ) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if max_candidates < 1 or min_holdouts < 1:
            raise ValueError("candidate and holdout limits must be positive")
        if not 0 <= minimum_improvement <= 1 or not 0 <= regression_tolerance <= 1:
            raise ValueError("thresholds must be between 0 and 1")
        self.memory = memory
        self.project = project.strip()
        self.max_candidates = max_candidates
        self.min_holdouts = min_holdouts
        self.minimum_improvement = minimum_improvement
        self.regression_tolerance = regression_tolerance
        self.continual = ContinualLearningGuard(memory, project)

    @staticmethod
    def compose(
        capabilities: Sequence[str],
        *,
        strategy: str,
        resource_lanes: Sequence[str],
        verification_depths: Sequence[str],
        max_candidates: int,
    ) -> tuple[CapabilityComposition, ...]:
        atoms = tuple(dict.fromkeys(str(x).strip() for x in capabilities if str(x).strip()))
        if not atoms:
            return ()
        lanes = tuple(dict.fromkeys(str(x).strip() for x in resource_lanes if str(x).strip())) or ("auto",)
        depths = tuple(dict.fromkeys(str(x).strip() for x in verification_depths if str(x).strip())) or ("standard",)
        rows: list[CapabilityComposition] = []
        seen: set[tuple[tuple[str, ...], str, str, str]] = set()
        for size in range(1, min(3, len(atoms)) + 1):
            for combo in combinations(atoms, size):
                for lane in lanes:
                    for depth in depths:
                        key = (combo, strategy, lane, depth)
                        if key in seen:
                            continue
                        seen.add(key)
                        cid = f"{strategy}:{lane}:{depth}:{'+'.join(combo)}"
                        rows.append(CapabilityComposition(cid, combo, strategy, lane, depth))
                        if len(rows) >= max_candidates:
                            return tuple(rows)
        return tuple(rows)

    @staticmethod
    def _validate_holdouts(
        results: Iterable[HoldoutResult],
        trigger_evidence: set[str],
        min_holdouts: int,
    ) -> tuple[HoldoutResult, ...]:
        rows = tuple(results)
        ids = {row.holdout_id for row in rows}
        if len(rows) != len(ids):
            raise ValueError("holdout ids must be unique")
        if len(rows) < min_holdouts:
            raise ValueError("insufficient unseen holdouts")
        if any(row.holdout_id in trigger_evidence for row in rows):
            raise ValueError("holdout set overlaps invention trigger evidence")
        if any(not row.verified for row in rows):
            raise ValueError("all holdout results must be independently verified")
        return rows

    def evaluate_candidate(
        self,
        composition: CapabilityComposition,
        holdout_results: Iterable[HoldoutResult],
        *,
        trigger_evidence: Iterable[str] = (),
        safety: SafetyResult | None = None,
    ) -> InventionCandidate:
        trigger = {str(x).strip() for x in trigger_evidence if str(x).strip()}
        holdouts = self._validate_holdouts(holdout_results, trigger, self.min_holdouts)
        candidate_score = mean(row.candidate_score for row in holdouts)
        incumbent_score = mean(row.incumbent_score for row in holdouts)
        improvement = candidate_score - incumbent_score
        regression_passed = all(
            row.candidate_score + self.regression_tolerance >= row.incumbent_score
            for row in holdouts
        )
        safety_passed = safety is not None and safety.passed
        verified = all(row.verified and bool(row.evidence_ids) for row in holdouts)
        reasons: list[str] = []
        if improvement < self.minimum_improvement:
            reasons.append("candidate did not beat incumbent by the minimum margin")
        if not regression_passed:
            reasons.append("candidate regressed on at least one holdout")
        if not safety_passed:
            reasons.append("safety gate failed or was not supplied")
        if not verified:
            reasons.append("holdout evidence is not fully verified")
        if safety is not None:
            reasons.extend(safety.reasons)
        return InventionCandidate(
            composition,
            holdouts,
            candidate_score,
            incumbent_score,
            improvement,
            regression_passed,
            safety_passed,
            verified,
            tuple(dict.fromkeys(reasons)),
        )

    def invent(
        self,
        problem: str,
        *,
        incumbent: CapabilityComposition,
        available_capabilities: Sequence[str],
        holdout_ids: Sequence[str],
        evaluate: Callable[[CapabilityComposition, str], HoldoutResult],
        safety_gate: Callable[[CapabilityComposition], SafetyResult],
        trigger_evidence: Iterable[str] = (),
        strategy: str = "default",
        resource_lanes: Sequence[str] = ("local", "agent"),
        verification_depths: Sequence[str] = ("standard", "deep", "independent"),
    ) -> InventionReceipt:
        if not problem.strip():
            raise ValueError("problem is required")
        holdouts = tuple(dict.fromkeys(str(x).strip() for x in holdout_ids if str(x).strip()))
        if len(holdouts) < self.min_holdouts:
            return InventionReceipt("blocked", problem, incumbent, None, (), ("insufficient unseen holdouts",))
        trigger = tuple(dict.fromkeys(str(x).strip() for x in trigger_evidence if str(x).strip()))
        candidates = self.compose(
            available_capabilities,
            strategy=strategy,
            resource_lanes=resource_lanes,
            verification_depths=verification_depths,
            max_candidates=self.max_candidates,
        )
        candidates = tuple(candidate for candidate in candidates if candidate.id != incumbent.id)
        evaluated: list[InventionCandidate] = []
        for candidate in candidates:
            rows = tuple(evaluate(candidate, holdout_id) for holdout_id in holdouts)
            safety = safety_gate(candidate)
            evaluated.append(self.evaluate_candidate(candidate, rows, trigger_evidence=trigger, safety=safety))
        viable = tuple(item for item in evaluated if item.regression_passed and item.safety_passed and item.verified and item.improvement >= self.minimum_improvement)
        if not viable:
            return InventionReceipt(
                "rejected",
                problem,
                incumbent,
                None,
                tuple(evaluated),
                ("no composition survived unseen-holdout, regression, and safety gates",),
            )
        selected = max(viable, key=lambda item: (item.improvement, item.candidate_score, item.composition.id))
        # Persist only the verified benchmark evidence. Execution authority remains elsewhere.
        observation = BenchmarkObservation(
            suite=f"autonomous-holdout:{problem.strip()}",
            capability="+".join(selected.composition.capabilities),
            version=selected.composition.id,
            score=selected.candidate_score,
            sample_count=len(selected.holdouts),
            evidence_ids=tuple(sorted({eid for row in selected.holdouts for eid in row.evidence_ids})),
            verified=selected.verified,
            approved=True,
        )
        regression = self.continual.compare(observation, tolerance=self.regression_tolerance)
        if not regression.accepted:
            return InventionReceipt(
                "rejected",
                problem,
                incumbent,
                selected,
                tuple(evaluated),
                ("continual-learning baseline rejected the candidate",),
            )
        self.continual.record(observation)
        return InventionReceipt(
            "graduated",
            problem,
            incumbent,
            selected,
            tuple(evaluated),
            ("candidate exceeded incumbent and survived regression and safety gates",),
            True,
        )


__all__ = [
    "AutonomousCapabilityInvention",
    "CapabilityComposition",
    "HoldoutResult",
    "InventionCandidate",
    "InventionReceipt",
    "SafetyResult",
]
