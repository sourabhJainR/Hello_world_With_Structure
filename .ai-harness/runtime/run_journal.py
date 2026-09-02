#!/usr/bin/env python3
"""Append-only execution journal and deterministic replay projection.

This is a lightweight local durability seam, not a workflow engine. Every harness telemetry event
can be mirrored here with a sequence number and hash-chain link. The journal survives process loss,
can be inspected without a provider, and gives resume/eval tooling a stable execution history.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

VERSION = "1.0"
_JOURNAL_NAME = "execution.journal.jsonl"
_HEADS: dict[str, tuple[int, str]] = {}


def _digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_head(path: Path) -> tuple[int, str]:
    key = str(path)
    if key in _HEADS:
        return _HEADS[key]
    if not path.exists():
        _HEADS[key] = (0, "")
        return _HEADS[key]
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 8192))
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                head = (int(row.get("sequence", 0)), str(row.get("hash", "")))
                _HEADS[key] = head
                return head
    except OSError:
        pass
    _HEADS[key] = (0, "")
    return _HEADS[key]


def append_event(run_dir: Path, event: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Append one durable event and return the journal record."""
    path = Path(run_dir) / _JOURNAL_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_sequence, previous_hash = _load_head(path)
    record = {
        "version": VERSION,
        "sequence": previous_sequence + 1,
        "timestamp": time.time(),
        "pid": os.getpid(),
        "event": str(event),
        "previous_hash": previous_hash,
        **fields,
    }
    record["hash"] = _digest(record)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    _HEADS[str(path)] = (record["sequence"], record["hash"])
    return record


def read_events(run_dir: Path) -> list[dict[str, Any]]:
    path = Path(run_dir) / _JOURNAL_NAME
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def verify_chain(run_dir: Path) -> dict[str, Any]:
    """Verify ordering and hash links without trusting model output."""
    rows = read_events(run_dir)
    reasons: list[str] = []
    previous = ""
    expected_sequence = 1
    for row in rows:
        if row.get("sequence") != expected_sequence:
            reasons.append("sequence_gap")
            break
        if row.get("previous_hash", "") != previous:
            reasons.append("hash_link_mismatch")
            break
        supplied_hash = row.get("hash")
        unsigned = dict(row)
        unsigned.pop("hash", None)
        if supplied_hash != _digest(unsigned):
            reasons.append("hash_mismatch")
            break
        previous = str(supplied_hash)
        expected_sequence += 1
    return {"passed": not reasons, "events": len(rows), "reasons": reasons, "head": previous}


def replay(run_dir: Path) -> dict[str, Any]:
    """Build a compact phase/run projection suitable for resume and evaluation tooling."""
    events = read_events(run_dir)
    phases: dict[str, dict[str, Any]] = {}
    status = "unknown"
    for row in events:
        event = str(row.get("event", ""))
        phase = row.get("phase")
        if phase:
            item = phases.setdefault(str(phase), {"starts": 0, "finishes": 0, "last": None})
            if event == "phase.start":
                item["starts"] += 1
            if event in {"provider.finish", "phase.finish"}:
                item["finishes"] += 1
            item["last"] = event
        if event == "run.finish":
            status = str(row.get("status", "unknown"))
        elif event in {"run.error", "run.crash"}:
            status = "failed"
    return {"version": VERSION, "status": status, "phases": phases, "events": len(events), "chain": verify_chain(run_dir)}
