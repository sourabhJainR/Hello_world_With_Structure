"""Deterministic quality contracts for specialist-agent work.

This module does not call an LLM. It evaluates structured evidence and review
findings so an agent cannot self-certify completion merely by producing text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

SEVERITIES = ("blocker", "material", "minor", "observation")
DEFAULT_RUBRIC: dict[str, object] = {
    "release_threshold": 90,
    "dimensions": {
        "correctness": 25,
        "completeness": 15,
        "evidence": 15,
        "verification": 15,
        "scope_discipline": 10,
        "security_and_safety": 10,
        "clarity": 5,
        "maintainability": 5,
    },
}


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    message: str
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown finding severity: {self.severity}")
        if not self.message.strip():
            raise ValueError("finding message must not be empty")


@dataclass
class QualityReceipt:
    score: int
    threshold: int
    hard_gates: dict[str, bool]
    findings: list[ReviewFinding] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold and all(self.hard_gates.values()) and not any(
            f.severity in {"blocker", "material"} for f in self.findings
        )

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "threshold": self.threshold,
            "passed": self.passed,
            "hard_gates": self.hard_gates,
            "findings": [
                {"severity": f.severity, "message": f.message, "evidence": f.evidence}
                for f in self.findings
            ],
            "evidence": self.evidence,
        }


def score_dimensions(dimensions: Mapping[str, int], rubric: Mapping[str, object]) -> int:
    """Validate and score dimension points without allowing values above rubric caps."""
    caps = rubric.get("dimensions", {})
    if not isinstance(caps, Mapping):
        raise ValueError("rubric dimensions must be a mapping")
    total = 0
    for name, cap in caps.items():
        try:
            cap_i = int(cap)
            value = int(dimensions.get(name, 0))
        except (TypeError, ValueError):
            raise ValueError(f"invalid score for dimension {name}") from None
        if value < 0 or value > cap_i:
            raise ValueError(f"dimension {name} must be between 0 and {cap_i}")
        total += value
    unknown = set(dimensions) - set(caps)
    if unknown:
        raise ValueError(f"unknown rubric dimensions: {sorted(unknown)}")
    return total


def evaluate(
    dimensions: Mapping[str, int],
    hard_gates: Mapping[str, bool],
    findings: Iterable[ReviewFinding] = (),
    evidence: Iterable[str] = (),
    rubric: Mapping[str, object] | None = None,
) -> QualityReceipt:
    """Produce a machine-readable quality receipt for a completed work unit."""
    rubric = rubric or DEFAULT_RUBRIC
    score = score_dimensions(dimensions, rubric)
    threshold = int(rubric.get("release_threshold", 90))
    normalized_findings = list(findings)
    normalized_evidence = [str(x) for x in evidence if str(x).strip()]
    gates = {str(k): bool(v) for k, v in hard_gates.items()}
    return QualityReceipt(score, threshold, gates, normalized_findings, normalized_evidence)
