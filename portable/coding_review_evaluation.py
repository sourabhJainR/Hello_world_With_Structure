"""Evidence-based evaluation and calibration for local coding reviews."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

@dataclass(frozen=True)
class CodingReviewObservation:
    review_id: str
    predicted_confidence: float
    finding_valid: bool
    evidence_grounded: bool
    actionable: bool
    regression_aware: bool
    hallucinated: bool = False
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise ValueError("review_id is required")
        if not isfinite(self.predicted_confidence) or not 0.0 <= self.predicted_confidence <= 1.0:
            raise ValueError("predicted_confidence must be between 0 and 1")
        if self.hallucinated and self.evidence_grounded:
            raise ValueError("hallucinated findings cannot be evidence-grounded")
        if self.verified and self.hallucinated:
            raise ValueError("hallucinated findings cannot be verified")

@dataclass(frozen=True)
class CodingReviewCalibration:
    samples: int
    validity_rate: float
    grounding_rate: float
    actionable_rate: float
    regression_awareness_rate: float
    hallucination_rate: float
    calibration_error: float
    usable: bool

    def as_dict(self) -> dict[str, float | int | bool]:
        return {"samples": self.samples, "validity_rate": round(self.validity_rate, 4),
                "grounding_rate": round(self.grounding_rate, 4),
                "actionable_rate": round(self.actionable_rate, 4),
                "regression_awareness_rate": round(self.regression_awareness_rate, 4),
                "hallucination_rate": round(self.hallucination_rate, 4),
                "calibration_error": round(self.calibration_error, 4),
                "usable": self.usable}

class CodingReviewEvaluator:
    """Evaluate local coding reviews using independently verified outcomes only."""

    def __init__(self, *, min_samples: int = 5, min_validity: float = 0.70,
                 max_hallucination: float = 0.10, max_calibration_error: float = 0.20) -> None:
        self.min_samples = max(1, int(min_samples))
        self.min_validity = max(0.0, min(1.0, float(min_validity)))
        self.max_hallucination = max(0.0, min(1.0, float(max_hallucination)))
        self.max_calibration_error = max(0.0, min(1.0, float(max_calibration_error)))

    def evaluate(self, observations: Iterable[CodingReviewObservation]) -> CodingReviewCalibration:
        rows = tuple(row for row in observations if row.verified)
        ids = [row.review_id for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate review_id")
        if not rows:
            return CodingReviewCalibration(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False)
        validity = sum(row.finding_valid for row in rows) / len(rows)
        grounding = sum(row.evidence_grounded for row in rows) / len(rows)
        actionable = sum(row.actionable for row in rows) / len(rows)
        regression = sum(row.regression_aware for row in rows) / len(rows)
        hallucination = sum(row.hallucinated for row in rows) / len(rows)
        calibration_error = sum(
            abs(row.predicted_confidence - float(row.finding_valid)) for row in rows
        ) / len(rows)
        usable = (len(rows) >= self.min_samples and validity >= self.min_validity
                  and hallucination <= self.max_hallucination
                  and calibration_error <= self.max_calibration_error)
        return CodingReviewCalibration(len(rows), validity, grounding, actionable,
                                       regression, hallucination, calibration_error, usable)

    def admission(self, calibration: CodingReviewCalibration) -> Mapping[str, object]:
        if not calibration.usable:
            return {"usable": False, "confidence_scale": 0.0,
                    "reason": "local coding review calibration is insufficient"}
        scale = min(1.0, calibration.validity_rate * (1.0 - calibration.hallucination_rate))
        return {"usable": True, "confidence_scale": round(scale, 4),
                "reason": "verified local coding review calibration is within bounds"}

__all__ = ["CodingReviewObservation", "CodingReviewCalibration", "CodingReviewEvaluator"]
