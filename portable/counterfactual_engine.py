"""Bounded counterfactual branch evaluation for future execution decisions.

The engine evaluates explicit candidate branches before execution. It does not
execute branches, mutate policy, or claim causal certainty. Its output is a
typed, auditable decision input for the existing DecisionFabric/Policy gates.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from .decision_fabric import ChoiceDecision, state_digest

@dataclass(frozen=True)
class BranchCandidate:
    name: str
    success_probability: float
    evidence_value: float
    cost: float = 0.5
    risk: float = 0.5
    confidence: float = 0.5
    expected_duration: float = 0.5
    resource_pressure: float = 0.0
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("branch name is required")
        for field in ("success_probability", "evidence_value", "cost", "risk", "confidence", "resource_pressure"):
            value = float(getattr(self, field))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field} must be between 0 and 1")
        if float(self.expected_duration) < 0.0:
            raise ValueError("expected_duration cannot be negative")

@dataclass(frozen=True)
class BranchScore:
    name: str
    utility: float
    relative_probability: float
    rationale: str

@dataclass(frozen=True)
class CounterfactualDecision:
    state_digest: str
    selected: str | None
    abstained: bool
    confidence: float
    margin: float
    branches: tuple[BranchScore, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "state_digest": self.state_digest,
            "selected": self.selected,
            "abstained": self.abstained,
            "confidence": round(self.confidence, 4),
            "margin": round(self.margin, 4),
            "branches": [
                {"name": item.name, "utility": round(item.utility, 4),
                 "relative_probability": round(item.relative_probability, 4),
                 "rationale": item.rationale}
                for item in self.branches
            ],
            "reason": self.reason,
        }

class CounterfactualEngine:
    """Compare explicit alternatives without executing them.

    The score favors successful, evidence-producing and lower-risk branches
    while accounting for cost, duration and resource pressure. These are
    decision heuristics, not claims of causal probability.
    """
    def __init__(self, *, min_confidence: float = 0.65, min_margin: float = 0.08) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if not 0.0 <= min_margin <= 1.0:
            raise ValueError("min_margin must be between 0 and 1")
        self.min_confidence = float(min_confidence)
        self.min_margin = float(min_margin)

    @staticmethod
    def _utility(branch: BranchCandidate) -> float:
        benefit = (
            branch.success_probability * branch.evidence_value
            * (1.0 - branch.risk) * (0.5 + 0.5 * branch.confidence)
        )
        penalties = (
            0.20 * branch.cost
            + 0.10 * min(1.0, branch.expected_duration)
            + 0.10 * branch.resource_pressure
        )
        return benefit - penalties

    def evaluate(self, state: Mapping[str, Any], branches: Sequence[BranchCandidate]) -> CounterfactualDecision:
        if not branches:
            raise ValueError("at least one counterfactual branch is required")
        names = [branch.name for branch in branches]
        if len(names) != len(set(names)):
            raise ValueError("branch names must be unique")
        utilities = [(branch, self._utility(branch)) for branch in branches]
        minimum = min(score for _, score in utilities)
        shifted = {branch.name: score - minimum + 0.01 for branch, score in utilities}
        total = sum(shifted.values())
        probabilities = {name: value / total for name, value in shifted.items()}
        ranked = sorted(utilities, key=lambda item: (-item[1], item[0].name))
        best_branch, best_utility = ranked[0]
        second_utility = ranked[1][1] if len(ranked) > 1 else best_utility - 1.0
        margin = max(0.0, min(1.0, best_utility - second_utility))
        confidence = max(0.0, min(1.0, best_branch.confidence * (0.5 + 0.5 * probabilities[best_branch.name])))
        abstained = confidence < self.min_confidence or (len(ranked) > 1 and margin < self.min_margin)
        reason = (
            "abstained because branch evidence/confidence was insufficient"
            if abstained else
            "selected highest-scoring branch after bounded counterfactual comparison"
        )
        scores = tuple(
            BranchScore(branch.name, utility, probabilities[branch.name], branch.rationale)
            for branch, utility in ranked
        )
        return CounterfactualDecision(
            state_digest(state), None if abstained else best_branch.name,
            abstained, confidence, margin, scores, reason
        )

    def as_choice(self, decision: CounterfactualDecision) -> ChoiceDecision | None:
        if decision.abstained or decision.selected is None:
            return None
        return ChoiceDecision(
            decision.selected,
            {item.name: item.relative_probability for item in decision.branches},
            decision.confidence,
        )

__all__ = ["BranchCandidate", "BranchScore", "CounterfactualDecision", "CounterfactualEngine"]
