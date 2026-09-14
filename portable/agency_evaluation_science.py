"""Dependency-free statistical primitives for agent evaluation."""
from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import mean, stdev
from typing import Iterable, Mapping


@dataclass(frozen=True)
class MetricSummary:
    name: str
    count: int
    mean: float
    stddev: float
    standard_error: float
    confidence_low: float
    confidence_high: float

    def as_dict(self) -> dict[str, float | int | str]:
        return self.__dict__.copy()


def summarize(name: str, values: Iterable[float], confidence_z: float = 1.96) -> MetricSummary:
    """Summarize samples without assuming their numeric range.

    Confidence intervals are intentionally not clipped to [0, 1]: paired deltas,
    latency changes, costs, and other evaluation metrics can be negative or exceed
    one. Range validation belongs to the metric-specific gate.
    """
    if not name.strip():
        raise ValueError("metric name is required")
    samples = [float(x) for x in values]
    if not samples:
        raise ValueError("at least one evaluation sample is required")
    if not all(math.isfinite(x) for x in samples):
        raise ValueError("evaluation samples must be finite")
    if confidence_z <= 0 or not math.isfinite(confidence_z):
        raise ValueError("confidence_z must be a finite positive value")
    average = mean(samples)
    deviation = stdev(samples) if len(samples) > 1 else 0.0
    error = deviation / math.sqrt(len(samples))
    margin = confidence_z * error
    return MetricSummary(name, len(samples), average, deviation, error, average - margin, average + margin)


def paired_delta(baseline: Iterable[float], candidate: Iterable[float]) -> MetricSummary:
    before = [float(x) for x in baseline]
    after = [float(x) for x in candidate]
    if len(before) != len(after) or not before:
        raise ValueError("paired evaluation requires equally sized non-empty samples")
    return summarize("paired_delta", (b - a for a, b in zip(before, after)))


def select_candidate(
    candidates: Mapping[str, Iterable[float]],
    *,
    minimum_mean: float = 0.0,
    minimum_samples: int = 1,
) -> tuple[str, tuple[MetricSummary, ...]]:
    if minimum_samples < 1:
        raise ValueError("minimum_samples must be positive")
    if not math.isfinite(float(minimum_mean)):
        raise ValueError("minimum_mean must be finite")
    summaries = tuple(summarize(name, values) for name, values in sorted(candidates.items()))
    eligible = [s for s in summaries if s.count >= minimum_samples and s.mean >= minimum_mean]
    if not eligible:
        raise ValueError("no candidate satisfies evaluation gates")
    winner = max(eligible, key=lambda s: (s.mean, s.confidence_low, -s.stddev, s.name))
    return winner.name, summaries
