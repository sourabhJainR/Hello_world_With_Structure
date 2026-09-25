"""Historical experience routing for bounded runtime decisions.

Experience is evidence, not authority. Durable observations remain owned by
LearningSteward; this module only reads them and converts them into typed
decision inputs. Deterministic policy remains the final authority.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .counterfactual_engine import BranchCandidate, CounterfactualEngine
from .decision_fabric import ChoiceDecision, DecisionFabric, DecisionQuestion, ScoreDecision
from .learning_steward import LearningSteward


@dataclass(frozen=True)
class ExperienceSummary:
    key: str
    samples: int
    success_rate: float
    evidence_quality: float
    avg_cost: float
    avg_latency: float
    failure_rate: float
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "samples": self.samples,
            "success_rate": round(self.success_rate, 3),
            "evidence_quality": round(self.evidence_quality, 3),
            "avg_cost": round(self.avg_cost, 3),
            "avg_latency": round(self.avg_latency, 3),
            "failure_rate": round(self.failure_rate, 3),
            "confidence": round(self.confidence, 3),
        }


class ExperienceRouter:
    """Read historical outcomes and produce bounded decisions."""

    def __init__(self, root: Path, *, minimum_samples: int = 3) -> None:
        self.root = Path(root)
        self.minimum_samples = max(1, int(minimum_samples))

    def summarize(self, key: str, *, limit: int = 60) -> ExperienceSummary | None:
        rows = LearningSteward.experience_history(self.root, key, limit=limit)
        if not rows:
            return None
        success = failures = 0
        evidence: list[float] = []
        costs: list[float] = []
        latencies: list[float] = []
        for row in rows:
            outcome = str(row.get("outcome", "")).lower()
            if outcome in {"worked", "passed", "success"}:
                success += 1
            elif outcome in {"failed", "regressed", "blocked"}:
                failures += 1
            detail = row.get("detail", "{}")
            try:
                payload = json.loads(str(detail))
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, Mapping):
                for target, bucket, default in (
                    ("evidence_quality", evidence, 0.0),
                    ("cost_score", costs, 1.0),
                    ("duration_seconds", latencies, 0.0),
                ):
                    try:
                        bucket.append(float(payload.get(target, default)))
                    except (TypeError, ValueError):
                        bucket.append(default)
        total = success + failures
        if total == 0:
            return None
        confidence = min(1.0, total / float(max(self.minimum_samples, 8)))
        return ExperienceSummary(
            key=key,
            samples=total,
            success_rate=(success + 1.0) / (total + 2.0),
            evidence_quality=max(0.0, min(1.0, sum(evidence) / len(evidence))) if evidence else 0.5,
            avg_cost=sum(costs) / len(costs) if costs else 0.5,
            avg_latency=sum(latencies) / len(latencies) if latencies else 0.0,
            failure_rate=(failures + 1.0) / (total + 2.0),
            confidence=confidence,
        )

    def choose_capability(
        self, capabilities: Sequence[str], *, key_prefix: str, risk: float = 0.2
    ) -> ChoiceDecision:
        if not capabilities:
            raise ValueError("capabilities cannot be empty")
        summaries = {name: self.summarize(f"{key_prefix}:capability:{name}") for name in capabilities}
        branches = [
            BranchCandidate(
                name=name,
                success_probability=summary.success_rate if summary else 0.5,
                evidence_value=summary.evidence_quality if summary else 0.5,
                cost=summary.avg_cost if summary else 0.5,
                risk=max(risk, summary.failure_rate if summary else 0.5),
                confidence=summary.confidence if summary else 0.25,
                expected_duration=min(1.0, summary.avg_latency / 300.0) if summary else 0.5,
                rationale="historical capability evidence" if summary else "cold-start prior",
            )
            for name, summary in summaries.items()
        ]
        engine = CounterfactualEngine(min_confidence=0.55, min_margin=0.03)
        decision = engine.evaluate({"key": key_prefix, "risk": risk}, branches)
        choice = engine.as_choice(decision)
        if choice is not None:
            return choice
        scores = {
            name: (
                1.0 / len(capabilities)
                if summary is None
                else max(
                    0.001,
                    0.55 * summary.success_rate
                    + 0.25 * summary.evidence_quality
                    + 0.15 * (1.0 - summary.avg_cost)
                    + 0.05 * (1.0 - risk * summary.failure_rate),
                )
            )
            for name, summary in summaries.items()
        }
        total = sum(scores.values())
        probabilities = {name: value / total for name, value in scores.items()}
        selected = max(probabilities, key=probabilities.get)
        return ChoiceDecision(selected, probabilities, max(probabilities.values()))

    def verification_depth(self, *, key: str, risk: float, evidence_quality: float) -> ScoreDecision:
        summary = self.summarize(f"{key}:verification")
        failure = summary.failure_rate if summary else 0.25
        pressure = max(float(risk), 1.0 - float(evidence_quality), failure)
        levels = ("standard", "deep", "independent", "human")
        costs = {"standard": 0.20, "deep": 0.40, "independent": 0.65, "human": 1.0}
        risks = {"standard": 0.65, "deep": 0.45, "independent": 0.25, "human": 0.05}
        evidence_bonus = {"standard": 0.0, "deep": 0.12, "independent": 0.22, "human": 0.30}
        branches = [
            BranchCandidate(
                level,
                max(0.05, 1.0 - pressure * risks[level]),
                min(1.0, evidence_quality + evidence_bonus[level]),
                costs[level],
                risks[level] * pressure,
                summary.confidence if summary else 0.45,
                costs[level],
                rationale=f"verification level {level}",
            )
            for level in levels
        ]
        engine = CounterfactualEngine(min_confidence=0.50, min_margin=0.04)
        decision = engine.evaluate({"key": key, "risk": risk, "failure_probability": failure}, branches)
        if decision.selected in levels and not decision.abstained:
            raw = {level: 0.05 for level in levels}
            raw[decision.selected] = 0.85
            total = sum(raw.values())
            return ScoreDecision(decision.selected, {k: v / total for k, v in raw.items()}, max(0.55, decision.confidence))
        if risk >= 0.9 or failure >= 0.75:
            selected = "human"
        elif pressure >= 0.72:
            selected = "independent"
        elif pressure >= 0.42:
            selected = "deep"
        else:
            selected = "standard"
        raw = {level: 0.05 for level in levels}
        raw[selected] = 0.85
        total = sum(raw.values())
        return ScoreDecision(selected, {k: v / total for k, v in raw.items()}, max(0.55, 1.0 - pressure * 0.35))

    def retry_or_escalate(self, *, key: str, risk: float, failure_probability: float) -> ChoiceDecision:
        options = ("retry", "escalate", "stop")
        branches = [
            BranchCandidate("retry", max(0.05, 1.0 - failure_probability * 0.55), 0.65, 0.35, min(1.0, risk * 0.75), max(0.35, 1.0 - failure_probability), 0.45),
            BranchCandidate("escalate", 0.90 if risk >= 0.75 else 0.75, 0.90, 0.75, 0.15, 0.70, 0.70),
            BranchCandidate("stop", max(0.05, 1.0 - failure_probability), 0.50, 0.10, min(1.0, risk), max(0.35, 1.0 - failure_probability), 0.10),
        ]
        engine = CounterfactualEngine(min_confidence=0.70, min_margin=0.04)
        decision = engine.evaluate({"key": key, "risk": risk, "failure_probability": failure_probability}, branches)
        choice = engine.as_choice(decision)
        if choice is not None:
            return choice
        selected = "escalate" if risk >= 0.9 or failure_probability >= 0.85 else ("retry" if failure_probability >= 0.55 else "stop")
        raw = {name: 0.05 for name in options}
        raw[selected] = 0.85
        total = sum(raw.values())
        return ChoiceDecision(selected, {k: v / total for k, v in raw.items()}, max(0.55, 1.0 - failure_probability * 0.4))

    def counterfactual(
        self, branches: Sequence[Mapping[str, Any]], *, state: Mapping[str, Any] | None = None
    ) -> ChoiceDecision:
        candidates = [
            BranchCandidate(
                name=str(branch["name"]),
                success_probability=float(branch.get("success_probability", 0.5)),
                evidence_value=float(branch.get("evidence_value", 0.5)),
                cost=float(branch.get("cost", 0.5)),
                risk=float(branch.get("risk", 0.5)),
                confidence=float(branch.get("confidence", 0.7)),
                expected_duration=float(branch.get("expected_duration", branch.get("duration", 0.5))),
                resource_pressure=float(branch.get("resource_pressure", 0.0)),
                rationale=str(branch.get("rationale", "")),
            )
            for branch in branches if str(branch.get("name", "")).strip()
        ]
        if not candidates:
            raise ValueError("branches require names")
        engine = CounterfactualEngine(min_confidence=0.45, min_margin=0.03)
        decision = engine.evaluate(state or {}, candidates)
        choice = engine.as_choice(decision)
        if choice is None:
            raise ValueError("counterfactual comparison abstained")
        return choice


__all__ = ["ExperienceRouter", "ExperienceSummary"]
