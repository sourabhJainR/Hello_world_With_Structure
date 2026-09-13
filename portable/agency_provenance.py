"""Persistent, append-only provenance ledger helpers for agency executions."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

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
        payload = {"sequence": self.sequence, "run_id": self.run_id, "event": self.event, "detail": self.detail, "artifact_ids": self.artifact_ids, "parent_hash": self.parent_hash}
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {"sequence": self.sequence, "run_id": self.run_id, "event": self.event, "detail": self.detail, "artifact_ids": list(self.artifact_ids), "parent_hash": self.parent_hash, "record_hash": self.record_hash}

@dataclass
class ProvenanceLedger:
    records: list[ProvenanceRecord] = field(default_factory=list)

    def append(self, run_id: str, event: str, detail: str = "", artifact_ids: Iterable[str] = ()) -> ProvenanceRecord:
        run_id, event = str(run_id).strip(), str(event).strip()
        if not run_id or not event:
            raise ValueError("run_id and event are required")
        previous = self.records[-1].record_hash if self.records else ""
        record = ProvenanceRecord(len(self.records) + 1, run_id, event, str(detail), tuple(sorted({str(x).strip() for x in artifact_ids if str(x).strip()})), previous)
        self.records.append(record)
        return record

    def verify(self) -> None:
        expected_parent = ""
        for index, record in enumerate(self.records, start=1):
            if record.sequence != index:
                raise ValueError("provenance sequence is not contiguous")
            if record.parent_hash != expected_parent:
                raise ValueError(f"broken provenance chain at sequence {record.sequence}")
            expected_parent = record.record_hash

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
            record = ProvenanceRecord(int(data["sequence"]), str(data["run_id"]), str(data["event"]), str(data["detail"]), tuple(str(x) for x in data["artifact_ids"]), str(data["parent_hash"]))
            if record.record_hash != data.get("record_hash"):
                raise ValueError(f"provenance record hash mismatch at sequence {record.sequence}")
            ledger.records.append(record)
        ledger.verify()
        return ledger

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.to_jsonl(), encoding="utf-8")

    @classmethod
    def read(cls, path: str | Path) -> "ProvenanceLedger":
        return cls.from_jsonl(Path(path).read_text(encoding="utf-8"))
