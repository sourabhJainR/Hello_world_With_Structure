"""Bounded predictive world-model policy.

Predictions are advisory signals derived from prior observed transitions. They
never override deterministic safety policy and abstain when evidence is weak.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .world_model import WorldModel, WorldPrediction

@dataclass(frozen=True)
class PredictionSignal:
    action: str
    prediction: WorldPrediction | None
    confidence: float
    abstained: bool
    reason: str

class PredictiveWorldPolicy:
    def __init__(self, world: WorldModel, *, min_samples: int = 2, min_confidence: float = 0.65,
                 min_calibration_samples: int = 3, min_calibration_accuracy: float = 0.5) -> None:
        self.world=world
        self.min_samples=max(1,int(min_samples))
        self.min_confidence=max(0.0,min(1.0,float(min_confidence)))
        self.min_calibration_samples=max(1,int(min_calibration_samples))
        self.min_calibration_accuracy=max(0.0,min(1.0,float(min_calibration_accuracy)))

    def forecast(self, entity_id: str, predicate: str, action: str, *, current_value: Any=None) -> PredictionSignal:
        prediction=self.world.predict_next(entity_id,predicate,action,current_value=current_value,min_samples=self.min_samples)
        if prediction is None:
            return PredictionSignal(action,None,0.0,True,"insufficient transition evidence")
        if prediction.confidence < self.min_confidence:
            return PredictionSignal(action,prediction,prediction.confidence,True,"prediction confidence below safety threshold")
        calibration = self.world.prediction_calibration(predicate=predicate, action=action)
        if (calibration["samples"] >= self.min_calibration_samples
                and calibration["accuracy"] < self.min_calibration_accuracy):
            return PredictionSignal(
                action, prediction, prediction.confidence, True,
                "historical prediction calibration below safety threshold",
            )
        return PredictionSignal(action,prediction,prediction.confidence,False,"bounded empirical prediction")

    def as_context(self, signal: PredictionSignal) -> Mapping[str, Any]:
        if signal.abstained:
            return {"available":False,"action":signal.action,"reason":signal.reason}
        return {"available":True,"action":signal.action,"predicted_value":signal.prediction.predicted_value,
                "confidence":round(signal.confidence,3),"evidence":list(signal.prediction.evidence_observation_ids),
                "reason":signal.reason}

__all__=["PredictionSignal","PredictiveWorldPolicy"]
