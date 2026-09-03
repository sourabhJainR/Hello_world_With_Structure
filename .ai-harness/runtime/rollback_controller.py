#!/usr/bin/env python3
"""Automatic degradation detection and safe policy rollback."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolicyHealth:
    policy_id: str
    baseline_acceptance: float
    current_acceptance: float
    baseline_regression_rate: float
    current_regression_rate: float


def should_rollback(health: PolicyHealth, *, acceptance_drop: float = 0.10, regression_increase: float = 0.05) -> bool:
    return (
        health.current_acceptance < health.baseline_acceptance - acceptance_drop
        or health.current_regression_rate > health.baseline_regression_rate + regression_increase
    )
