"""Validation-only adapter for the canonical engineering evidence ledger."""
from __future__ import annotations

from dataclasses import dataclass
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

__all__ = ["CONFIDENCE", "EvidenceClaim", "EvidenceSpine", "KINDS", "evidence_from_state"]
