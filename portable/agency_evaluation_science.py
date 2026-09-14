"""Scientific evaluation primitives inspired by Agent Evaluation chapters.

Keeps evaluation deterministic and dependency-free: repeated scores can be
summarized with confidence intervals, paired deltas, and a conservative
selection rule rather than relying on one lucky run.
"""
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
    samples = [float(x) for x in values]
    if not samples:
        raise ValueError("at least one evaluation sample is required")
    if confidence_z <= 0:
        raise ValueError("confidence_z must be positive")
    average = mean(samples)
    deviation = stdev(samples) if len(samples) > 1 else 0.0
    error = deviation / math.sqrt(len(samples)) if samples else 0.0
    margin = confidence_z * error
    return MetricSummary(name, len(samples), average, deviation, error, max(0.0, average - margin), min(1.0, average + margin))


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
    summaries = tuple(summarize(name, values) for name, values in candidates.items())
    eligible = [s for s in summaries if s.count >= minimum_samples and s.mean >= minimum_mean]
    if not eligible:
        raise ValueError("no candidate satisfies evaluation gates")
    winner = max(eligible, key=lambda s: (s.mean, s.confidence_low, -s.stddev, s.name))
    return winner.name, summaries
