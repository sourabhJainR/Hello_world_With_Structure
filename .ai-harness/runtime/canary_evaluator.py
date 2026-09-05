#!/usr/bin/env python3
"""Deterministic shadow/canary evaluation with bounded staged rollout."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Any
import json

try:
    from .learning_engine import PolicyCandidate
    from .regression_replay import ReplayCase
except ImportError:
    from learning_engine import PolicyCandidate
    from regression_replay import ReplayCase


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    case_id: str
    mode: str
    success: bool
    verified: bool
    latency_ms: float = 0.0
    token_cost: float = 0.0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    policy_id: str
    mode: str
    total: int
    passed: int
    failed: int
    verified: int
    avg_latency_ms: float
    avg_token_cost: float
    pass_rate: float
    verification_rate: float
    gate_passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanaryStage:
    stage: int
    exposure: float
    total: int
    pass_rate: float
    verification_rate: float
    gate_passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanaryPlan:
    policy_id: str
    stages: tuple[CanaryStage, ...]
    promoted: bool
    halted_at: int | None
    reason: str


def evaluate_shadow(candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any]) -> EvaluationReport:
    return _evaluate(candidate, cases, runner, mode="shadow")


def evaluate_canary(candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any], *, min_pass_rate: float = 1.0, min_verification_rate: float = 1.0) -> EvaluationReport:
    report = _evaluate(candidate, cases, runner, mode="canary")
    gate = report.total > 0 and report.pass_rate >= min_pass_rate and report.verification_rate >= min_verification_rate
    return EvaluationReport(**{**asdict(report), "gate_passed": gate})


def evaluate_staged_canary(
    candidate: PolicyCandidate,
    cases: Iterable[ReplayCase],
    runner: Callable[[ReplayCase, PolicyCandidate], Any],
    *,
    exposures: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 1.0),
    min_cases_per_stage: int = 3,
    min_pass_rate: float = 1.0,
    min_verification_rate: float = 1.0,
) -> CanaryPlan:
    """Progress only when every bounded stage passes; halt on first regression."""
    all_cases = list(cases)
    stages: list[CanaryStage] = []
    for index, exposure in enumerate(exposures, start=1):
        if not all_cases:
            return CanaryPlan(candidate.policy_id, tuple(stages), False, index, "empty-canary-corpus")
        count = max(min_cases_per_stage, int(round(len(all_cases) * max(0.0, min(1.0, exposure)))))
        selected = all_cases[:min(len(all_cases), count)]
        report = evaluate_canary(candidate, selected, runner, min_pass_rate=min_pass_rate, min_verification_rate=min_verification_rate)
        stage = CanaryStage(index, exposure, report.total, report.pass_rate, report.verification_rate, report.gate_passed, report.failures)
        stages.append(stage)
        if not report.gate_passed:
            return CanaryPlan(candidate.policy_id, tuple(stages), False, index, "canary-gate-failed")
    return CanaryPlan(candidate.policy_id, tuple(stages), True, None, "all-canary-stages-passed")


def _evaluate(candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any], *, mode: str) -> EvaluationReport:
    outcomes: list[EvaluationOutcome] = []
    failures: list[str] = []
    for case in cases:
        try:
            raw = runner(case, candidate)
            success, verified, latency_ms, token_cost, error = _normalize(raw)
        except Exception as exc:
            success, verified, latency_ms, token_cost, error = False, False, 0.0, 0.0, f"runner error: {exc}"
        outcome = EvaluationOutcome(case.case_id, mode, success, verified, latency_ms, token_cost, error)
        outcomes.append(outcome)
        if success != case.expected_success or verified != case.expected_verification:
            failures.append(case.case_id)

    total = len(outcomes)
    passed = total - len(failures)
    verified = sum(x.verified for x in outcomes)
    return EvaluationReport(
        policy_id=candidate.policy_id, mode=mode, total=total, passed=passed, failed=total - passed,
        verified=verified, avg_latency_ms=round(sum(x.latency_ms for x in outcomes) / total, 3) if total else 0.0,
        avg_token_cost=round(sum(x.token_cost for x in outcomes) / total, 3) if total else 0.0,
        pass_rate=round(passed / total, 3) if total else 0.0,
        verification_rate=round(verified / total, 3) if total else 0.0,
        gate_passed=not failures and total > 0, failures=tuple(failures),
    )


def _normalize(raw: Any) -> tuple[bool, bool, float, float, str | None]:
    if isinstance(raw, dict):
        return bool(raw.get("success")), bool(raw.get("verified")), float(raw.get("latency_ms", 0) or 0), float(raw.get("token_cost", 0) or 0), str(raw["error"]) if raw.get("error") else None
    if isinstance(raw, tuple):
        values = list(raw)
        return (bool(values[0]) if values else False, bool(values[1]) if len(values) > 1 else False,
                float(values[2]) if len(values) > 2 else 0.0, float(values[3]) if len(values) > 3 else 0.0,
                str(values[4]) if len(values) > 4 and values[4] else None)
    raise TypeError("runner must return a tuple or mapping")


def report_json(report: EvaluationReport) -> str:
    return json.dumps(asdict(report), sort_keys=True)
