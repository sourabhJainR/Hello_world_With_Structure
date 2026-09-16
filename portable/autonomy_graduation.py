"""Evidence-driven autonomy graduation gates.

This module decides whether evidence satisfies a configured graduation policy.
It never grants permissions, changes execution policy, or bypasses the host.
"""
from __future__ import annotations

from dataclasses import dataclass

from .agi_evaluation import EvaluationReport
from .self_model import CapabilityProfile

LEVELS = ("assisted", "bounded", "supervised", "graduated")


@dataclass(frozen=True)
class GraduationPolicy:
    min_coverage: int = 10
    min_pass_rate: float = 0.95
    min_observations: int = 20
    min_confidence: float = 0.90
    require_regression_pass: bool = True
    require_safety_review: bool = True
    require_human_approval: bool = True

    def __post_init__(self) -> None:
        if self.min_coverage < 1 or self.min_observations < 1:
            raise ValueError("coverage and observation thresholds must be positive")
        if not 0 <= self.min_pass_rate <= 1 or not 0 <= self.min_confidence <= 1:
            raise ValueError("rate thresholds must be between 0 and 1")


@dataclass(frozen=True)
class AutonomyEvidence:
    evaluation: EvaluationReport
    self_profile: CapabilityProfile
    regression_passed: bool
    safety_reviewed: bool
    human_approved: bool


@dataclass(frozen=True)
class GraduationReceipt:
    level: str
    eligible: bool
    grants_permission: bool
    reasons: tuple[str, ...]


class AutonomyGraduator:
    """Evaluate graduation readiness while leaving authority with the host."""

    def evaluate(self, level: str, evidence: AutonomyEvidence, policy: GraduationPolicy | None = None) -> GraduationReceipt:
        if level not in LEVELS:
            raise ValueError(f"unknown autonomy level: {level}")
        if not isinstance(evidence, AutonomyEvidence):
            raise ValueError("evidence must be AutonomyEvidence")
        policy = policy or GraduationPolicy()
        reasons: list[str] = []
        if evidence.evaluation.total == 0 or len(evidence.evaluation.coverage) < policy.min_coverage:
            reasons.append("evaluation coverage below gate")
        if evidence.evaluation.pass_rate < policy.min_pass_rate:
            reasons.append("evaluation pass-rate below gate")
        if evidence.self_profile.observations < policy.min_observations:
            reasons.append("self-model observation count below gate")
        if evidence.self_profile.confidence < policy.min_confidence:
            reasons.append("self-model confidence below gate")
        if policy.require_regression_pass and not evidence.regression_passed:
            reasons.append("regression gate failed")
        if policy.require_safety_review and not evidence.safety_reviewed:
            reasons.append("safety review is required")
        if policy.require_human_approval and not evidence.human_approved:
            reasons.append("human approval is required")
        return GraduationReceipt(level, not reasons, False, tuple(reasons))


__all__ = ["AutonomyEvidence", "AutonomyGraduator", "GraduationPolicy", "GraduationReceipt", "LEVELS"]
