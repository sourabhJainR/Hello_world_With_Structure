"""Deterministic engineering-design gate distilled from classic software-design guidance.

The guard does not attempt to judge code with heuristics or reproduce any book.
It checks whether a task has declared the design facts that matter for its risk:
ownership, boundaries, data semantics, failure behavior, compatibility, and
verification. It produces a compact receipt that can be attached to AER evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping


class DesignDimension(str, Enum):
    COMPLEXITY = "complexity"
    ARCHITECTURE = "architecture"
    DOMAIN = "domain"
    DATA = "data"
    RESILIENCE = "resilience"
    REFACTORING = "refactoring"
    LEGACY = "legacy"
    CONSTRUCTION = "construction"
    COMPATIBILITY = "compatibility"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class DesignFinding:
    dimension: DesignDimension
    severity: FindingSeverity
    message: str
    evidence_key: str | None = None


@dataclass(frozen=True)
class DesignReviewReceipt:
    intent_digest: str
    dimensions: tuple[str, ...]
    declared: Mapping[str, str]
    findings: tuple[DesignFinding, ...]
    status: str
    receipt_digest: str

    @property
    def blocking(self) -> bool:
        return any(f.severity == FindingSeverity.BLOCKING for f in self.findings)


class EngineeringDesignGuard:
    """Infer and validate the minimum design contract for a change.

    ``design`` is a small mapping supplied by the planner/agent. Values should
    state facts, decisions, or explicit ``not_applicable: reason`` declarations.
    The guard never treats model prose as proof; it only checks that the required
    contract was declared so later verification/review can test it.
    """

    _DIMENSION_KEYS = {
        DesignDimension.COMPLEXITY: ("complexity", "module", "abstraction"),
        DesignDimension.ARCHITECTURE: ("architecture", "boundary", "dependency"),
        DesignDimension.DOMAIN: ("domain", "bounded_context", "aggregate", "invariant"),
        DesignDimension.DATA: ("data", "source_of_truth", "consistency", "idempotency", "ordering"),
        DesignDimension.RESILIENCE: ("resilience", "timeout", "retry", "recovery", "observability"),
        DesignDimension.REFACTORING: ("refactoring", "behavior_delta", "safety_net", "smell"),
        DesignDimension.LEGACY: ("legacy", "characterization", "seam", "dependency_break"),
        DesignDimension.CONSTRUCTION: ("construction", "validation", "error_handling", "test"),
        DesignDimension.COMPATIBILITY: ("compatibility", "rollout", "migration", "contract"),
    }

    _PATH_RULES = (
        (re.compile(r"(^|/)(domain|domains|aggregate|entity|value_object)(/|$)|bounded[_-]?context", re.I), {DesignDimension.DOMAIN}),
        (re.compile(r"(^|/)(db|database|storage|repository|migration|schema|cache|queue|event|stream|consumer|producer)(/|$)|(^|_)(sql|cdc|replica|projection)(_|$)", re.I), {DesignDimension.DATA}),
        (re.compile(r"(^|/)(api|client|gateway|adapter|integration|http|grpc|worker|job|queue|deploy|infra|ops)(/|$)|timeout|retry|circuit|health", re.I), {DesignDimension.RESILIENCE, DesignDimension.ARCHITECTURE}),
        (re.compile(r"test|spec|fixture|mock|stub|refactor", re.I), {DesignDimension.CONSTRUCTION, DesignDimension.REFACTORING}),
        (re.compile(r"legacy|compat|migration|upgrade|deprecat", re.I), {DesignDimension.LEGACY, DesignDimension.COMPATIBILITY}),
        (re.compile(r"(^|/)(controller|handler|service|use[_-]?case|application)(/|$)", re.I), {DesignDimension.ARCHITECTURE, DesignDimension.CONSTRUCTION}),
    )

    _HIGH_RISK = {"high", "critical"}

    @staticmethod
    def intent_digest(intent: str) -> str:
        return hashlib.sha256(intent.strip().encode("utf-8")).hexdigest()

    @classmethod
    def infer_dimensions(cls, intent: str, changed_paths: Iterable[str], risk: str = "medium") -> tuple[DesignDimension, ...]:
        text = f"{intent} {' '.join(changed_paths)}".lower()
        dimensions: set[DesignDimension] = {DesignDimension.COMPLEXITY, DesignDimension.CONSTRUCTION}
        for pattern, found in cls._PATH_RULES:
            if pattern.search(text):
                dimensions.update(found)

        keyword_rules = {
            DesignDimension.DOMAIN: r"\b(domain|bounded context|aggregate|invariant|ubiquitous language)\b",
            DesignDimension.DATA: r"\b(database|schema|cache|queue|event|stream|replicat|consistency|durab|partition)\b",
            DesignDimension.RESILIENCE: r"\b(timeout|retry|backoff|circuit|bulkhead|load shedding|failure|outage|health)\b",
            DesignDimension.REFACTORING: r"\b(refactor|rename|extract|cleanup|smell|restructure)\b",
            DesignDimension.LEGACY: r"\b(legacy|untested|characterization|seam|brownfield)\b",
            DesignDimension.COMPATIBILITY: r"\b(api|contract|migration|upgrade|backward|compatib|rollout|version)\b",
            DesignDimension.ARCHITECTURE: r"\b(architect|boundary|dependency|adapter|framework|service|module|layer)\b",
        }
        for dimension, pattern in keyword_rules.items():
            if re.search(pattern, text, re.I):
                dimensions.add(dimension)

        if risk.lower() in cls._HIGH_RISK:
            dimensions.update({DesignDimension.ARCHITECTURE, DesignDimension.RESILIENCE, DesignDimension.COMPATIBILITY})
        return tuple(sorted(dimensions, key=lambda d: d.value))

    @classmethod
    def review(
        cls,
        *,
        intent: str,
        changed_paths: Iterable[str] = (),
        design: Mapping[str, str] | None = None,
        risk: str = "medium",
        blocking_dimensions: Iterable[DesignDimension] = (DesignDimension.RESILIENCE,),
    ) -> DesignReviewReceipt:
        paths = tuple(changed_paths)
        dimensions = cls.infer_dimensions(intent, paths, risk)
        declared = {str(k): str(v).strip() for k, v in (design or {}).items() if str(v).strip()}
        blocking_set = set(blocking_dimensions)
        findings: list[DesignFinding] = []

        for dimension in dimensions:
            keys = cls._DIMENSION_KEYS[dimension]
            matching = next((key for key in keys if key in declared), None)
            if matching is None:
                severity = FindingSeverity.BLOCKING if dimension in blocking_set and risk.lower() in cls._HIGH_RISK else FindingSeverity.WARNING
                findings.append(DesignFinding(dimension, severity, f"Declare {dimension.value} evidence or an explicit not_applicable reason", None))
                continue
            value = declared[matching]
            if value.lower().startswith("not_applicable"):
                if ":" not in value and " - " not in value:
                    findings.append(DesignFinding(dimension, FindingSeverity.WARNING, "not_applicable must include a reason", matching))
            else:
                findings.append(DesignFinding(dimension, FindingSeverity.INFO, f"design contract declared for {dimension.value}", matching))

        if DesignDimension.REFACTORING in dimensions and not any(k in declared for k in ("behavior_delta", "safety_net")):
            findings.append(DesignFinding(DesignDimension.REFACTORING, FindingSeverity.WARNING, "Refactoring work should state behavior delta and safety net"))
        if DesignDimension.DATA in dimensions and not any(k in declared for k in ("source_of_truth", "consistency", "idempotency")):
            findings.append(DesignFinding(DesignDimension.DATA, FindingSeverity.WARNING, "Data changes should state ownership and retry/consistency semantics"))
        if DesignDimension.RESILIENCE in dimensions and not any(k in declared for k in ("timeout", "retry", "recovery")):
            severity = FindingSeverity.BLOCKING if risk.lower() in cls._HIGH_RISK else FindingSeverity.WARNING
            findings.append(DesignFinding(DesignDimension.RESILIENCE, severity, "External/asynchronous work should state timeout, retry, and recovery behavior"))

        status = "blocked" if any(f.severity == FindingSeverity.BLOCKING for f in findings) else ("review_required" if any(f.severity == FindingSeverity.WARNING for f in findings) else "ready")
        payload = {
            "intent_digest": cls.intent_digest(intent),
            "dimensions": [d.value for d in dimensions],
            "declared": dict(sorted(declared.items())),
            "findings": [f.__dict__ | {"dimension": f.dimension.value, "severity": f.severity.value} for f in findings],
            "status": status,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        return DesignReviewReceipt(cls.intent_digest(intent), tuple(d.value for d in dimensions), declared, tuple(findings), status, digest)

    @staticmethod
    def as_evidence(receipt: DesignReviewReceipt) -> dict[str, object]:
        """Return a provenance-friendly projection without mutable receipt state."""
        return {
            "kind": "engineering_design_review",
            "digest": receipt.receipt_digest,
            "intent_digest": receipt.intent_digest,
            "dimensions": list(receipt.dimensions),
            "status": receipt.status,
            "findings": [
                {"dimension": f.dimension.value, "severity": f.severity.value, "message": f.message, "evidence_key": f.evidence_key}
                for f in receipt.findings
            ],
        }
