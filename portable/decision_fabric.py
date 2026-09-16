"""Provider-neutral decision primitives for machine-native agent control.

The fabric borrows the useful interface idea behind System One models: when
software needs a judgment, do not force a text generator to emit prose and
then parse it. Ask typed questions and return probabilities that deterministic
policy code can consume.

This module is deliberately provider-neutral. It does not claim to implement
Jev or RLCD. A host can adapt an external decision model later, while tests and
local development can use deterministic evaluators.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class ChoiceDecision:
    selected: str
    probabilities: Mapping[str, float]
    confidence: float

    def __post_init__(self) -> None:
        if not self.selected or self.selected not in self.probabilities:
            raise ValueError("selected must be one of the choices")
        _validate_distribution(self.probabilities)
        _validate_probability(self.confidence, "confidence")


@dataclass(frozen=True)
class ScoreDecision:
    level: str
    probabilities: Mapping[str, float]
    confidence: float

    def __post_init__(self) -> None:
        if not self.level or self.level not in self.probabilities:
            raise ValueError("level must be one of the score levels")
        _validate_distribution(self.probabilities)
        _validate_probability(self.confidence, "confidence")


@dataclass(frozen=True)
class NoulDecision:
    probability_true: float
    confidence: float

    def __post_init__(self) -> None:
        _validate_probability(self.probability_true, "probability_true")
        _validate_probability(self.confidence, "confidence")


@dataclass(frozen=True)
class DecisionQuestion:
    key: str
    kind: str
    options: tuple[str, ...] = ()
    levels: tuple[str, ...] = ()
    claim: str = ""

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("question key is required")
        if self.kind not in {"choice", "score", "noul"}:
            raise ValueError("kind must be choice, score, or noul")
        if self.kind == "choice" and not self.options:
            raise ValueError("choice questions require options")
        if self.kind == "score" and not self.levels:
            raise ValueError("score questions require levels")
        if self.kind == "noul" and not self.claim.strip():
            raise ValueError("noul questions require a claim")


@dataclass(frozen=True)
class DecisionBatch:
    state_digest: str
    decisions: Mapping[str, ChoiceDecision | ScoreDecision | NoulDecision]

    def __post_init__(self) -> None:
        if not self.state_digest:
            raise ValueError("state_digest is required")


Evaluator = Callable[[Mapping[str, Any], DecisionQuestion], ChoiceDecision | ScoreDecision | NoulDecision]


def _validate_probability(value: float, label: str) -> None:
    if not isinstance(value, (int, float)) or not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")


def _validate_distribution(values: Mapping[str, float]) -> None:
    if not values:
        raise ValueError("probability distribution cannot be empty")
    total = 0.0
    for key, value in values.items():
        if not str(key).strip():
            raise ValueError("distribution keys must be non-empty")
        _validate_probability(float(value), f"probability[{key}]")
        total += float(value)
    if abs(total - 1.0) > 1e-6:
        raise ValueError("probabilities must sum to 1")


def state_digest(state: Mapping[str, Any]) -> str:
    import hashlib
    import json
    payload = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class DecisionFabric:
    """Evaluate many typed questions over one shared state.

    The questions are independent by contract. A provider adapter may evaluate
    them in parallel; the default implementation simply invokes the evaluator
    once per question while preserving one shared state digest.
    """

    def __init__(self, evaluator: Evaluator) -> None:
        self.evaluator = evaluator

    def evaluate(self, state: Mapping[str, Any], questions: Sequence[DecisionQuestion]) -> DecisionBatch:
        if not questions:
            raise ValueError("at least one decision question is required")
        digest = state_digest(state)
        results: dict[str, ChoiceDecision | ScoreDecision | NoulDecision] = {}
        for question in questions:
            if question.key in results:
                raise ValueError(f"duplicate question key: {question.key}")
            decision = self.evaluator(state, question)
            self._validate_result(question, decision)
            results[question.key] = decision
        return DecisionBatch(digest, results)

    @staticmethod
    def _validate_result(question: DecisionQuestion, decision: object) -> None:
        if question.kind == "choice":
            if not isinstance(decision, ChoiceDecision) or set(decision.probabilities) != set(question.options):
                raise ValueError(f"choice evaluator returned an incompatible result for {question.key}")
        elif question.kind == "score":
            if not isinstance(decision, ScoreDecision) or set(decision.probabilities) != set(question.levels):
                raise ValueError(f"score evaluator returned an incompatible result for {question.key}")
        elif not isinstance(decision, NoulDecision):
            raise ValueError(f"noul evaluator returned an incompatible result for {question.key}")


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    allowed: bool
    reason: str
    confidence: float


class DecisionPolicy:
    """Turn fuzzy judgments into deterministic, auditable actions."""

    def __init__(self, *, min_confidence: float = 0.70) -> None:
        _validate_probability(min_confidence, "min_confidence")
        self.min_confidence = float(min_confidence)

    def gate(self, *, action: str, decision: ChoiceDecision | ScoreDecision | NoulDecision, require: str | None = None) -> PolicyDecision:
        confidence = float(decision.confidence)
        if confidence < self.min_confidence:
            return PolicyDecision(action, False, "confidence below policy threshold", confidence)
        if require is not None:
            if isinstance(decision, NoulDecision):
                passed = decision.probability_true >= self.min_confidence if require == "true" else decision.probability_true < (1.0 - self.min_confidence)
            elif isinstance(decision, (ChoiceDecision, ScoreDecision)):
                passed = decision.selected == require if isinstance(decision, ChoiceDecision) else decision.level == require
            else:
                passed = False
            if not passed:
                return PolicyDecision(action, False, f"required condition '{require}' was not met", confidence)
        return PolicyDecision(action, True, "typed decision passed policy gate", confidence)


__all__ = [
    "ChoiceDecision", "DecisionBatch", "DecisionFabric", "DecisionPolicy", "DecisionQuestion",
    "NoulDecision", "PolicyDecision", "ScoreDecision", "state_digest",
]
