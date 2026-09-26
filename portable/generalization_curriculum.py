"""Bounded experiment curriculum for measuring capability generalization.

The curriculum generator turns a capability claim into independent probes across
related task families. It does not execute arbitrary code or grant authority;
callers supply the evaluator. Experiment selection favors novelty and expected
information gain while remaining deterministic and budgeted.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


def _clean(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class GeneralizationExperiment:
    id: str
    task_family: str
    condition: str
    novelty: float
    difficulty: float


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    score: float
    evidence_id: str
    verified: bool = True


@dataclass(frozen=True)
class GeneralizationReport:
    capability: str
    baseline_score: float
    results: tuple[ExperimentResult, ...]
    family_scores: tuple[tuple[str, float], ...]
    generalization_score: float
    generalized: bool
    reasons: tuple[str, ...] = ()


class GeneralizationCurriculum:
    """Generate independent probes and score cross-family transfer."""

    def __init__(self, *, max_experiments: int = 12) -> None:
        if max_experiments < 2:
            raise ValueError("max_experiments must be at least 2")
        self.max_experiments = max_experiments

    def generate(
        self,
        capability: str,
        task_families: Sequence[str],
        *,
        conditions: Sequence[str] = ("novel-input", "constraint-shift", "composition"),
    ) -> tuple[GeneralizationExperiment, ...]:
        capability = _clean(capability, "capability")
        families = tuple(dict.fromkeys(_clean(x, "task_family") for x in task_families))
        conditions = tuple(dict.fromkeys(_clean(x, "condition") for x in conditions))
        if len(families) < 2:
            raise ValueError("at least two task families are required")
        if not conditions:
            raise ValueError("at least one condition is required")
        experiments = []
        for family in families:
            for condition in conditions:
                raw = f"{capability}|{family}|{condition}"
                digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
                novelty = 0.5 + (int(digest[:4], 16) / 65535.0) * 0.5
                difficulty = 0.5 + (int(digest[4:8], 16) / 65535.0) * 0.5
                experiments.append(GeneralizationExperiment(
                    id=f"gen-{digest}", task_family=family, condition=condition,
                    novelty=novelty, difficulty=difficulty,
                ))
        experiments.sort(key=lambda x: (-x.novelty, -x.difficulty, x.id))
        # Ensure every family remains represented when the budget is smaller
        # than the full curriculum.
        selected = []
        for family in families:
            match = next((x for x in experiments if x.task_family == family), None)
            if match is not None:
                selected.append(match)
        selected_ids = {x.id for x in selected}
        selected.extend(x for x in experiments if x.id not in selected_ids)
        return tuple(selected[: self.max_experiments])

    def evaluate(
        self,
        capability: str,
        experiments: Iterable[GeneralizationExperiment],
        evaluator: Callable[[GeneralizationExperiment], ExperimentResult],
        *,
        baseline_score: float,
        minimum_family_score: float = 0.70,
        minimum_generalization_score: float = 0.75,
    ) -> GeneralizationReport:
        capability = _clean(capability, "capability")
        if not 0 <= baseline_score <= 1:
            raise ValueError("baseline_score must be between 0 and 1")
        if not 0 <= minimum_family_score <= 1 or not 0 <= minimum_generalization_score <= 1:
            raise ValueError("score thresholds must be between 0 and 1")
        unique = {}
        for experiment in experiments:
            unique[experiment.id] = experiment
        if len(unique) < 2:
            raise ValueError("at least two independent experiments are required")
        results = []
        for experiment in unique.values():
            result = evaluator(experiment)
            if not isinstance(result, ExperimentResult) or result.experiment_id != experiment.id:
                raise TypeError("evaluator must return a matching ExperimentResult")
            if not 0 <= result.score <= 1:
                raise ValueError("experiment score must be between 0 and 1")
            if not result.evidence_id.strip():
                raise ValueError("experiment evidence is required")
            results.append(result)
        families = {}
        for experiment, result in ((unique[r.experiment_id], r) for r in results):
            families.setdefault(experiment.task_family, []).append(result.score)
        family_scores = tuple(sorted((family, sum(scores) / len(scores)) for family, scores in families.items()))
        generalization = sum(r.score for r in results) / len(results)
        below_baseline = sum(1 for r in results if r.score + 0.02 < baseline_score)
        generalized = (
            len(family_scores) >= 2
            and all(score >= minimum_family_score for _, score in family_scores)
            and generalization >= minimum_generalization_score
            and below_baseline == 0
            and all(r.verified for r in results)
        )
        reasons = []
        if len(family_scores) < 2:
            reasons.append("insufficient task-family diversity")
        if any(score < minimum_family_score for _, score in family_scores):
            reasons.append("one or more task families failed the quality threshold")
        if generalization < minimum_generalization_score:
            reasons.append("aggregate generalization score below threshold")
        if below_baseline:
            reasons.append("at least one independent experiment regressed baseline")
        if any(not r.verified for r in results):
            reasons.append("unverified experiment evidence")
        return GeneralizationReport(
            capability, baseline_score, tuple(results), family_scores,
            generalization, generalized, tuple(reasons),
        )


__all__ = [
    "GeneralizationCurriculum", "GeneralizationExperiment",
    "ExperimentResult", "GeneralizationReport",
]
