"""Deterministic deeper benchmarking for general capability evaluation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from .agi_evaluation import KINDS


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    kind: str
    expected: str
    observed: str
    evidence: tuple[str, ...]
    confidence: float
    difficulty: str
    domain: str

    def __post_init__(self) -> None:
        for name, value in (("case_id", self.case_id), ("expected", self.expected), ("observed", self.observed),
                            ("difficulty", self.difficulty), ("domain", self.domain)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.kind not in KINDS:
            raise ValueError("unknown benchmark kind")
        if not self.evidence or any(not isinstance(item, str) or not item.strip() for item in self.evidence):
            raise ValueError("benchmark evidence is required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class DeepBenchmarkReport:
    total: int
    passed: int
    failed: int
    coverage: tuple[str, ...]
    per_kind: dict[str, float]
    per_domain: dict[str, float]
    per_difficulty: dict[str, float]
    evidence_rate: float
    calibration_mae: float
    adversarial_pass_rate: float | None
    domains: tuple[str, ...]
    digest: str

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def missing_kinds(self) -> tuple[str, ...]:
        return tuple(sorted(KINDS.difference(self.coverage)))


class DeepEvaluator:
    """Run benchmark cases and expose granular, replay-friendly metrics."""

    def run(self, cases: Iterable[BenchmarkCase], *, required_kinds: Iterable[str] = ()) -> DeepBenchmarkReport:
        materialized = list(cases)
        seen: set[str] = set()
        for case in materialized:
            if case.case_id in seen:
                raise ValueError("duplicate benchmark case id")
            seen.add(case.case_id)
        required = tuple(sorted(set(required_kinds)))
        if any(kind not in KINDS for kind in required):
            raise ValueError("unknown required benchmark kind")
        coverage = tuple(sorted({case.kind for case in materialized}))
        missing = sorted(set(required).difference(coverage))
        if missing:
            raise ValueError(f"missing required benchmark kinds: {', '.join(missing)}")

        passed = [case for case in materialized if case.expected.strip() == case.observed.strip()]
        def rate(group: list[BenchmarkCase]) -> float:
            return sum(case.expected.strip() == case.observed.strip() for case in group) / len(group) if group else 0.0

        per_kind = {kind: rate([case for case in materialized if case.kind == kind]) for kind in coverage}
        per_domain = {domain: rate([case for case in materialized if case.domain == domain]) for domain in sorted({case.domain for case in materialized})}
        per_difficulty = {difficulty: rate([case for case in materialized if case.difficulty == difficulty]) for difficulty in sorted({case.difficulty for case in materialized})}
        calibration = sum(abs(case.confidence - float(case in passed)) for case in materialized) / len(materialized) if materialized else 0.0
        adversarial = [case for case in materialized if case.kind == "adversarial"]
        canonical = [
            {"case_id": case.case_id, "kind": case.kind, "expected": case.expected.strip(), "observed": case.observed.strip(),
             "evidence": tuple(sorted(case.evidence)), "confidence": case.confidence, "difficulty": case.difficulty, "domain": case.domain}
            for case in sorted(materialized, key=lambda item: item.case_id)
        ]
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return DeepBenchmarkReport(
            len(materialized), len(passed), len(materialized) - len(passed), coverage, per_kind, per_domain,
            per_difficulty, 1.0 if materialized else 0.0, round(calibration, 6), rate(adversarial) if adversarial else None,
            tuple(sorted({case.domain for case in materialized})), digest,
        )


__all__ = ["BenchmarkCase", "DeepBenchmarkReport", "DeepEvaluator"]
