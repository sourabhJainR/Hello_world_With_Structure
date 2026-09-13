"""Provider-neutral validators for specialist-agent result metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .agency_quality import ReviewFinding


@dataclass(frozen=True)
class ValidationResult:
    hard_gates: dict[str, bool]
    findings: list[ReviewFinding]
    checks: tuple[str, ...]


def _has_external_research_source(evidence: list[Mapping[str, object]]) -> bool:
    """Require explicit source attribution rather than model-generated claims."""
    for item in evidence:
        source = str(item.get("source", "")).strip().lower()
        locator = str(item.get("locator", "")).strip()
        if locator:
            return True
        if source and source not in {"model", "llm", "assistant", "generated", "self"}:
            return True
    return False


def validate_result(
    artifact_type: str,
    deliverables: list[str],
    evidence: list[Mapping[str, object]],
    verification: list[str],
    metadata: Mapping[str, object] | None = None,
) -> ValidationResult:
    """Apply deterministic domain expectations without executing untrusted work."""
    metadata = metadata or {}
    findings: list[ReviewFinding] = []
    checks: list[str] = []
    gates = {
        "deliverable_present": bool(deliverables),
        "evidence_present": bool(evidence),
        "verification_present": bool(verification),
        "acceptance": bool(metadata.get("acceptance", True)),
    }

    if artifact_type == "code":
        checks.extend(("tests-or-static-analysis", "scope-diff", "compatibility"))
        if not any(any(k in str(v).lower() for k in ("test", "static", "lint", "build")) for v in verification):
            findings.append(ReviewFinding("material", "code work lacks explicit test/static/build verification"))
    elif artifact_type == "research":
        checks.extend(("source-backed-claims", "uncertainty-labels"))
        if not _has_external_research_source(evidence):
            findings.append(ReviewFinding("material", "research result lacks source-backed evidence"))
    elif artifact_type == "design":
        checks.extend(("requirements", "accessibility", "responsive-or-contextual-verification"))
    elif artifact_type in {"finance", "analytics"}:
        checks.extend(("inputs", "calculation-basis", "scenario-boundaries"))
        if not metadata.get("calculation_basis"):
            findings.append(ReviewFinding("material", "analytical result lacks a stated calculation basis"))
    elif artifact_type == "security":
        checks.extend(("permission-boundary", "secret-safety", "negative-path-verification"))
        if metadata.get("permission_bypass"):
            findings.append(ReviewFinding("blocker", "permission bypass was reported"))
        if metadata.get("secrets_exposed"):
            findings.append(ReviewFinding("blocker", "secret exposure was reported"))
    else:
        checks.append("general-evidence-and-verification")

    return ValidationResult(gates, findings, tuple(checks))
