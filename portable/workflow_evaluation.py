"""Provider-neutral workflow evaluation for probabilistic engineering decisions."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class DecisionObservation:
    decision_id: str
    predicted_probability: float
    observed_outcome: bool
    expected_probability: float | None = None
    abstained: bool = False
    latency_ms: int = 0
    token_cost: int = 0
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("decision_id is required")
        for label, value in (("predicted_probability", self.predicted_probability), ("expected_probability", self.expected_probability)):
            if value is None:
                continue
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be between 0 and 1")
        if self.latency_ms < 0 or self.token_cost < 0:
            raise ValueError("latency_ms and token_cost cannot be negative")
        if self.abstained and self.verified:
            raise ValueError("abstained decisions cannot be marked verified")


@dataclass(frozen=True)
class WorkflowEvaluation:
    observations: tuple[DecisionObservation, ...]

    @classmethod
    def from_iterable(cls, values: Iterable[DecisionObservation]) -> "WorkflowEvaluation":
        rows = tuple(values)
        ids = [row.decision_id for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate decision_id")
        return cls(rows)

    def accuracy(self) -> float:
        eligible = [row for row in self.observations if not row.abstained]
        if not eligible:
            return 0.0
        return sum((row.predicted_probability >= 0.5) == row.observed_outcome for row in eligible) / len(eligible)

    def brier_score(self) -> float:
        if not self.observations:
            return 0.0
        return sum((row.predicted_probability - float(row.observed_outcome)) ** 2 for row in self.observations) / len(self.observations)

    def calibration_error(self, bins: int = 10) -> float:
        if bins < 1:
            raise ValueError("bins must be positive")
        if not self.observations:
            return 0.0
        buckets: list[list[DecisionObservation]] = [[] for _ in range(bins)]
        for row in self.observations:
            index = min(bins - 1, int(row.predicted_probability * bins))
            buckets[index].append(row)
        total = len(self.observations)
        error = 0.0
        for bucket in buckets:
            if not bucket:
                continue
            confidence = sum(row.predicted_probability for row in bucket) / len(bucket)
            outcome_rate = sum(float(row.observed_outcome) for row in bucket) / len(bucket)
            error += abs(confidence - outcome_rate) * len(bucket) / total
        return error

    def abstention_rate(self) -> float:
        if not self.observations:
            return 0.0
        return sum(row.abstained for row in self.observations) / len(self.observations)

    def summary(self) -> dict[str, float | int]:
        return {
            "observation_count": len(self.observations),
            "accuracy": self.accuracy(),
            "brier_score": self.brier_score(),
            "calibration_error": self.calibration_error(),
            "abstention_rate": self.abstention_rate(),
            "average_latency_ms": sum(row.latency_ms for row in self.observations) / len(self.observations) if self.observations else 0.0,
            "average_token_cost": sum(row.token_cost for row in self.observations) / len(self.observations) if self.observations else 0.0,
        }


__all__ = ["DecisionObservation", "WorkflowEvaluation"]
