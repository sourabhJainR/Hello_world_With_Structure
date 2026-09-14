"""Persistent, append-only provenance ledger helpers for agency executions."""
from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ProvenanceRecord:
    sequence: int
    run_id: str
    event: str
    detail: str = ""
    artifact_ids: tuple[str, ...] = ()
    parent_hash: str = ""

    @property
    def record_hash(self) -> str:
        return sha256(
            json.dumps(
                {
                    "sequence": self.sequence,
                    "run_id": self.run_id,
                    "event": self.event,
                    "detail": self.detail,
                    "artifact_ids": self.artifact_ids,
                    "parent_hash": self.parent_hash,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "run_id": self.run_id,
            "event": self.event,
            "detail": self.detail,
            "artifact_ids": list(self.artifact_ids),
            "parent_hash": self.parent_hash,
            "record_hash": self.record_hash,
        }


@dataclass
class ProvenanceLedger:
    records: list[ProvenanceRecord] = field(default_factory=list)

    def append(
        self,
        run_id: str,
        event: str,
        detail: str = "",
        artifact_ids: Iterable[str] = (),
    ) -> ProvenanceRecord:
        run_id, event = str(run_id).strip(), str(event).strip()
        if not run_id or not event:
            raise ValueError("run_id and event are required")
        record = ProvenanceRecord(
            len(self.records) + 1,
            run_id,
            event,
            str(detail),
            tuple(sorted({str(x).strip() for x in artifact_ids if str(x).strip()})),
            self.records[-1].record_hash if self.records else "",
        )
        self.records.append(record)
        return record

    def append_evidence_event(
        self,
        *,
        run_id: str,
        event: str,
        context_evidence_digest: str = "",
        detail: Mapping[str, object] | None = None,
        artifact_ids: Iterable[str] = (),
    ) -> ProvenanceRecord:
        """Append a structured lifecycle event while preserving evidence lineage."""
        payload: dict[str, object] = dict(detail or {})
        if context_evidence_digest:
            payload["context_evidence_digest"] = str(context_evidence_digest)
        return self.append(
            run_id=run_id,
            event=event,
            detail=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            artifact_ids=artifact_ids,
        )

    def verify(self) -> None:
        parent = ""
        for i, record in enumerate(self.records, 1):
            if record.sequence != i:
                raise ValueError("provenance sequence is not contiguous")
            if record.parent_hash != parent:
                raise ValueError(f"broken provenance chain at sequence {record.sequence}")
            expected = record.record_hash
            if not expected:
                raise ValueError("empty provenance hash")
            parent = expected

    def to_jsonl(self) -> str:
        self.verify()
        return "".join(json.dumps(r.as_dict(), sort_keys=True) + "\n" for r in self.records)

    @classmethod
    def from_jsonl(cls, text: str) -> "ProvenanceLedger":
        ledger = cls()
        for line in text.splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            expected = {"sequence", "run_id", "event", "detail", "artifact_ids", "parent_hash", "record_hash"}
            if set(data) != expected or not isinstance(data["artifact_ids"], list):
                raise ValueError("invalid provenance record schema")
            record = ProvenanceRecord(
                int(data["sequence"]),
                str(data["run_id"]),
                str(data["event"]),
                str(data["detail"]),
                tuple(str(x) for x in data["artifact_ids"]),
                str(data["parent_hash"]),
            )
            if record.record_hash != data["record_hash"]:
                raise ValueError(f"provenance record hash mismatch at sequence {record.sequence}")
            ledger.records.append(record)
        ledger.verify()
        return ledger

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.to_jsonl(), encoding="utf-8")

    @classmethod
    def read(cls, path: str | Path) -> "ProvenanceLedger":
        return cls.from_jsonl(Path(path).read_text(encoding="utf-8"))
