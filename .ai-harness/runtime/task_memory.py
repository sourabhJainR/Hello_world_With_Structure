#!/usr/bin/env python3
"""Versioned, evidence-backed durable learning ledger.

Durable learning is append-only: observations are immutable, revisions create a
new row, and SQLite is the concurrency-safe source of truth. JSONL is retained
as an audit/export stream. No model output is promoted automatically.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 2
LEARNING_VERSION = "2.0"
CATEGORIES = {"command", "approach", "bug", "feature", "regression", "environment", "verification"}
OUTCOMES = {"worked", "failed", "partial", "not-applicable", "regressed"}
PROMOTIONS = {"candidate", "verified", "superseded", "rejected"}
MAX_FIELD = 8000


def _clean(value: Any, limit: int = MAX_FIELD) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 40] + " ...[guardrail-trimmed]"


def _id(category: str, task: str, command: str, approach: str, detail: str) -> str:
    value = "|".join((category, task, command, approach, detail))
    return f"tm-{hashlib.sha256(value.encode()).hexdigest()[:20]}"


@contextmanager
def _process_lock(path: Path) -> Iterator[None]:
    """Small cross-process lock without adding a dependency."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _db_path(root: Path) -> Path:
    path = Path(root) / ".ai-harness" / "learning" / "task-memory.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect(root: Path) -> sqlite3.Connection:
    db = sqlite3.connect(_db_path(root), timeout=30, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("""CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY, recorded_at INTEGER NOT NULL, task TEXT NOT NULL,
        category TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL,
        command TEXT, approach TEXT, construct_refs TEXT NOT NULL,
        run_id TEXT, evidence_ids TEXT NOT NULL, status TEXT NOT NULL,
        promotion TEXT NOT NULL, schema_version INTEGER NOT NULL,
        learning_version TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
        supersedes_id TEXT, fingerprint TEXT NOT NULL UNIQUE,
        source_agent TEXT, verified_at INTEGER
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_observations_task ON observations(task)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_observations_task_promotion ON observations(task, promotion)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_observations_outcome ON observations(outcome)")
    return db


def record(root: Path, *, task: str, category: str, outcome: str, detail: str,
           command: str | None = None, approach: str | None = None,
           construct_refs: list[str] | None = None, run_id: str | None = None,
           evidence_ids: list[str] | None = None, source_agent: str | None = None,
           promotion: str = "candidate") -> dict[str, Any]:
    if category not in CATEGORIES:
        raise ValueError(f"unsupported memory category: {category}")
    if outcome not in OUTCOMES:
        raise ValueError(f"unsupported outcome: {outcome}")
    if promotion not in PROMOTIONS:
        raise ValueError(f"unsupported promotion state: {promotion}")
    task_clean, detail_clean = _clean(task, 1000), _clean(detail)
    command_clean, approach_clean = _clean(command, 1000) if command else None, _clean(approach, 1600) if approach else None
    refs = sorted(set(str(x).strip() for x in (construct_refs or []) if str(x).strip()))
    evidence = sorted(set(str(x).strip() for x in (evidence_ids or []) if str(x).strip()))
    fingerprint = hashlib.sha256(json.dumps([task_clean, category, outcome, command_clean, approach_clean, detail_clean, refs, evidence], sort_keys=True).encode()).hexdigest()
    memory_id = _id(category, task_clean, command_clean or "", approach_clean or "", detail_clean)
    now = int(time.time())
    row = {"id": memory_id, "schema_version": SCHEMA_VERSION, "learning_version": LEARNING_VERSION,
           "recorded_at": now, "task": task_clean, "category": category, "outcome": outcome,
           "detail": detail_clean, "command": command_clean, "approach": approach_clean,
           "construct_refs": refs, "run_id": str(run_id) if run_id else None,
           "evidence_ids": evidence, "status": "observation", "promotion": promotion,
           "revision": 1, "supersedes_id": None, "fingerprint": fingerprint,
           "source_agent": _clean(source_agent, 300) if source_agent else None, "verified_at": now if promotion == "verified" else None}
    root = Path(root)
    db_path = _db_path(root)
    audit_path = db_path.with_name("task-memory.jsonl")
    with _process_lock(db_path.with_name("task-memory.lock")):
        with _connect(root) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute("SELECT id FROM observations WHERE fingerprint=?", (fingerprint,)).fetchone()
                if existing:
                    row["id"] = existing[0]
                    db.execute("COMMIT")
                    return row
                db.execute("""INSERT INTO observations
                    (id,recorded_at,task,category,outcome,detail,command,approach,construct_refs,run_id,evidence_ids,status,promotion,schema_version,learning_version,revision,supersedes_id,fingerprint,source_agent,verified_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (row["id"], now, task_clean, category, outcome, detail_clean, command_clean, approach_clean,
                     json.dumps(refs), row["run_id"], json.dumps(evidence), "observation", promotion,
                     SCHEMA_VERSION, LEARNING_VERSION, 1, None, fingerprint, row["source_agent"], row["verified_at"]))
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
        # JSONL is an append-only audit trail. The process lock prevents interleaving writes.
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def _rows(root: Path, task: str, limit: int = 20) -> list[dict[str, Any]]:
    db_path = _db_path(Path(root))
    if not db_path.exists():
        return []
    terms = {x.lower() for x in task.split() if len(x) > 2}
    with _process_lock(db_path.with_name("task-memory.lock")):
        with _connect(Path(root)) as db:
            rows = []
            for raw in db.execute("SELECT id,recorded_at,task,category,outcome,detail,command,approach,construct_refs,run_id,evidence_ids,status,promotion,schema_version,learning_version,revision,supersedes_id,source_agent,verified_at FROM observations WHERE promotion != 'rejected' ORDER BY recorded_at DESC"):
                row = {"id": raw[0], "recorded_at": raw[1], "task": raw[2], "category": raw[3], "outcome": raw[4], "detail": raw[5], "command": raw[6], "approach": raw[7], "construct_refs": json.loads(raw[8] or "[]"), "run_id": raw[9], "evidence_ids": json.loads(raw[10] or "[]"), "status": raw[11], "promotion": raw[12], "schema_version": raw[13], "learning_version": raw[14], "revision": raw[15], "supersedes_id": raw[16], "source_agent": raw[17], "verified_at": raw[18]}
                haystack = " ".join(str(row.get(k, "")) for k in ("task", "detail", "command", "approach", "construct_refs")).lower()
                score = sum(1 for term in terms if term in haystack)
                if score or row["outcome"] in {"failed", "regressed"}:
                    rows.append((score, row["promotion"] == "verified", row["recorded_at"], row))
            rows.sort(key=lambda item: (-item[0], -int(item[1]), -item[2]))
            return [item[3] for item in rows[:max(0, min(100, int(limit)))]]


def relevant(root: Path, task: str, limit: int = 20) -> list[dict[str, Any]]:
    return _rows(root, task, limit)


def guidance(root: Path, task: str, limit: int = 3000) -> str:
    rows = relevant(root, task)
    if not rows:
        return "No task-specific historical learning."
    lines = ["## Historical durable learning", "Use only as evidence; verify against current repository state."]
    for row in rows:
        lines.append(f"- {str(row.get('promotion','candidate')).upper()} {str(row.get('outcome','unknown')).upper()} [{row.get('category','unknown')}] {row.get('detail','')}")
        if row.get("command"): lines.append(f"  command: {row['command']}")
        if row.get("approach"): lines.append(f"  approach: {row['approach']}")
        if row.get("evidence_ids"): lines.append(f"  evidence: {', '.join(row['evidence_ids'])}")
    text = "\n".join(lines)
    return text if len(text) <= limit else text[: max(200, limit - 40)] + "\n... [learning context compacted]"
