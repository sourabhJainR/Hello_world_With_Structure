"""Validation-only adapters for the canonical engineering evidence ledger."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

CONFIDENCE = {"high", "medium", "low"}
KINDS = {"source", "test", "runtime", "history", "documentation", "external", "tool"}

@dataclass(frozen=True)
class EvidenceClaim:
    id: str
    kind: str
    source: str
    claim: str
    confidence: str
    locator: str = ""
    snapshot: str = ""
    freshness: str = ""
    provenance: str = ""

    def validate(self) -> None:
        if not self.id or not self.source or not self.claim:
            raise ValueError("evidence id, source, and claim are required")
        if self.kind not in KINDS:
            raise ValueError(f"invalid evidence kind: {self.kind}")
        if self.confidence not in CONFIDENCE:
            raise ValueError(f"invalid evidence confidence: {self.confidence}")
        if not self.snapshot:
            raise ValueError(f"evidence snapshot is required: {self.id}")
        if not self.provenance:
            raise ValueError(f"evidence provenance is required: {self.id}")

@dataclass(frozen=True)
class DecisionRecord:
    id: str
    decision: str
    evidence_ids: tuple[str, ...]
    typed_output: str = ""
    probability: float | None = None
    calibration_group: str = ""
    model_id: str = ""
    method: str = ""
    abstained: bool = False
    observed_outcome: bool | None = None

    def validate(self, known_evidence: Iterable[str] = ()) -> None:
        if not self.id or not self.decision:
            raise ValueError("decision id and decision are required")
        if not self.evidence_ids:
            raise ValueError(f"decision evidence is required: {self.id}")
        available = set(known_evidence)
        if available and any(evidence_id not in available for evidence_id in self.evidence_ids):
            raise ValueError(f"decision references missing evidence: {self.id}")
        if self.probability is not None and (not isfinite(self.probability) or not 0.0 <= self.probability <= 1.0):
            raise ValueError(f"decision probability must be between 0 and 1: {self.id}")
        if self.probability is not None and not self.model_id:
            raise ValueError(f"probabilistic decision requires model_id: {self.id}")
        if self.abstained and self.observed_outcome is not None:
            raise ValueError(f"abstained decision cannot carry an observed outcome: {self.id}")

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "decision": self.decision,
            "evidence_ids": list(self.evidence_ids),
            "typed_output": self.typed_output,
            "probability": self.probability,
            "calibration_group": self.calibration_group,
            "model_id": self.model_id,
            "method": self.method,
            "abstained": self.abstained,
            "observed_outcome": self.observed_outcome,
        }

class EvidenceSpine:
    """Validated in-memory view over canonical evidence records; not a store."""
    def __init__(self, claims: Iterable[EvidenceClaim] = ()) -> None:
        rows = tuple(claims)
        for claim in rows:
            claim.validate()
        ids = [claim.id for claim in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence id")
        self._claims = {claim.id: claim for claim in rows}

    @property
    def claims(self) -> Mapping[str, EvidenceClaim]:
        return self._claims

    def require(self, evidence_id: str) -> EvidenceClaim:
        try:
            return self._claims[evidence_id]
        except KeyError as exc:
            raise ValueError(f"missing evidence: {evidence_id}") from exc

    def validate_references(self, references: Iterable[object], *, repository_snapshot: str | None = None) -> None:
        for reference in references:
            evidence_id = getattr(reference, "evidence_id", None)
            snapshot = getattr(reference, "snapshot", "")
            if not isinstance(evidence_id, str) or not evidence_id:
                raise ValueError("evidence reference id is required")
            claim = self.require(evidence_id)
            if snapshot and snapshot != claim.snapshot:
                raise ValueError(f"evidence snapshot mismatch: {evidence_id}")
            if repository_snapshot and claim.snapshot != repository_snapshot:
                raise ValueError(f"stale evidence for repository snapshot: {evidence_id}")

def evidence_from_state(rows: Iterable[Mapping[str, object]]) -> EvidenceSpine:
    return EvidenceSpine(
        EvidenceClaim(
            id=str(row.get("id", "")),
            kind=str(row.get("kind", "")),
            source=str(row.get("source", "")),
            claim=str(row.get("claim", "")),
            confidence=str(row.get("confidence", "")),
            locator=str(row.get("locator", "")),
            snapshot=str(row.get("snapshot", "")),
            freshness=str(row.get("freshness", "")),
            provenance=str(row.get("provenance", "")),
        ) for row in rows
    )

def decisions_from_state(rows: Iterable[Mapping[str, object]], *, evidence_ids: Iterable[str] = ()) -> tuple[DecisionRecord, ...]:
    available = tuple(evidence_ids)
    decisions = tuple(
        DecisionRecord(
            id=str(row.get("id", "")),
            decision=str(row.get("decision", "")),
            evidence_ids=tuple(str(x) for x in row.get("evidence_ids", ())),
            typed_output=str(row.get("typed_output", "")),
            probability=float(row["probability"]) if row.get("probability") is not None else None,
            calibration_group=str(row.get("calibration_group", "")),
            model_id=str(row.get("model_id", "")),
            method=str(row.get("method", "")),
            abstained=bool(row.get("abstained", False)),
            observed_outcome=row.get("observed_outcome") if isinstance(row.get("observed_outcome"), bool) else None,
        ) for row in rows
    )
    seen: set[str] = set()
    for decision in decisions:
        decision.validate(available)
        if decision.id in seen:
            raise ValueError(f"duplicate decision id: {decision.id}")
        seen.add(decision.id)
    return decisions

__all__ = ["CONFIDENCE", "DecisionRecord", "EvidenceClaim", "EvidenceSpine", "KINDS", "decisions_from_state", "evidence_from_state"]
