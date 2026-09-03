#!/usr/bin/env python3
"""Durable evidence ledger for commands, approaches, outcomes, misses and regressions.

This is a learning input store, not an autonomous policy editor. Entries remain
advisory until repeated evidence promotes them through the normal learning flow.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

VERSION = "1.0"
CATEGORIES = {"command", "approach", "bug", "feature", "regression", "environment", "verification"}


def _compact(value: Any, limit: int = 1200) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit - 20] + " ...[trimmed]"


def _id(kind: str, task: str, value: str) -> str:
    return f"tm-{hashlib.sha256(f'{kind}|{task}|{value}'.encode()).hexdigest()[:16]}"


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def record(root: Path, *, task: str, category: str, outcome: str, detail: str, command: str | None = None, approach: str | None = None, construct_refs: list[str] | None = None, run_id: str | None = None, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    if category not in CATEGORIES:
        raise ValueError(f"unsupported memory category: {category}")
    if outcome not in {"worked", "failed", "partial", "not-applicable", "regressed"}:
        raise ValueError(f"unsupported outcome: {outcome}")
    now = int(time.time())
    value = _compact(detail)
    row = {
        "id": _id(category, task, (command or "") + "|" + (approach or "") + "|" + value),
        "schema_version": 1,
        "learning_version": VERSION,
        "recorded_at": now,
        "task": _compact(task, 500),
        "category": category,
        "outcome": outcome,
        "detail": value,
        "command": _compact(command, 500) if command else None,
        "approach": _compact(approach, 800) if approach else None,
        "construct_refs": sorted(set(str(x) for x in (construct_refs or []) if str(x).strip())),
        "run_id": str(run_id) if run_id else None,
        "evidence_ids": sorted(set(str(x) for x in (evidence_ids or []) if str(x).strip())),
        "status": "observation",
        "promotion": "requires-repeated-evidence",
    }
    _append(Path(root) / ".ai-harness" / "learning" / "task-memory.jsonl", row)
    return row


def relevant(root: Path, task: str, limit: int = 20) -> list[dict[str, Any]]:
    path = Path(root) / ".ai-harness" / "learning" / "task-memory.jsonl"
    if not path.exists():
        return []
    terms = {x.lower() for x in task.split() if len(x) > 2}
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        haystack = " ".join(str(row.get(k, "")) for k in ("task", "detail", "command", "approach", "construct_refs")).lower()
        score = sum(1 for term in terms if term in haystack)
        if score or row.get("outcome") in {"failed", "regressed"}:
            rows.append((score, int(row.get("recorded_at", 0)), row))
    rows.sort(key=lambda item: (-item[0], -item[1]))
    return [item[2] for item in rows[:max(0, min(100, int(limit)))]]


def guidance(root: Path, task: str, limit: int = 3000) -> str:
    rows = relevant(root, task)
    if not rows:
        return "No task-specific historical command or approach observations."
    lines = ["## Historical task evidence", "Use these observations as evidence, not as unquestionable truth."]
    for row in rows:
        result = str(row.get("outcome", "unknown")).upper()
        command = f" command={row['command']}" if row.get("command") else ""
        approach = f" approach={row['approach']}" if row.get("approach") else ""
        lines.append(f"- {result} [{row.get('category', 'unknown')}] {row.get('detail', '')}{command}{approach}")
    text = "\n".join(lines)
    return text if len(text) <= limit else text[:limit - 40] + "\n... [historical evidence compacted]"
