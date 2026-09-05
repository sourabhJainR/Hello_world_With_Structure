#!/usr/bin/env python3
"""Durable, evidence-backed regression knowledge shared by learning and replay."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import time


@dataclass(frozen=True, slots=True)
class RegressionKnowledge:
    knowledge_id: str
    task_family: str
    component: str = ""
    subsystem: str = ""
    failure_signature: str = ""
    invariant: str = ""
    symptom: str = ""
    reproduction: str = ""
    fix: str = ""
    test_pointer: str = ""
    evidence_pointer: str = ""
    severity: str = "medium"
    confidence: float = 0.0
    source_kind: str = "observation"
    source_ref: str = ""
    status: str = "active"
    created_at: int = 0
    updated_at: int = 0


class RegressionMemory:
    """Small SQLite-backed knowledge base; only verified evidence becomes active."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS regression_knowledge (
                knowledge_id TEXT PRIMARY KEY, task_family TEXT NOT NULL, component TEXT NOT NULL,
                subsystem TEXT NOT NULL, failure_signature TEXT NOT NULL, invariant TEXT NOT NULL,
                symptom TEXT NOT NULL, reproduction TEXT NOT NULL, fix TEXT NOT NULL,
                test_pointer TEXT NOT NULL, evidence_pointer TEXT NOT NULL, severity TEXT NOT NULL,
                confidence REAL NOT NULL, source_kind TEXT NOT NULL, source_ref TEXT NOT NULL,
                status TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_reg_task ON regression_knowledge(task_family, status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_reg_component ON regression_knowledge(component, status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_reg_signature ON regression_knowledge(failure_signature, status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_reg_invariant ON regression_knowledge(invariant, status)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def fingerprint(*, task_family: str, component: str = "", failure_signature: str = "", invariant: str = "") -> str:
        payload = "|".join(str(x).strip().lower() for x in (task_family, component, failure_signature, invariant))
        return sha256(payload.encode()).hexdigest()[:24]

    def record(self, item: RegressionKnowledge, *, verified: bool = False) -> str:
        now = int(time.time())
        status = "active" if verified and item.confidence >= 0.80 and item.test_pointer and item.evidence_pointer else "pending"
        row = RegressionKnowledge(item.knowledge_id or self.fingerprint(task_family=item.task_family, component=item.component,
            failure_signature=item.failure_signature, invariant=item.invariant), item.task_family, item.component,
            item.subsystem, item.failure_signature, item.invariant, item.symptom, item.reproduction, item.fix,
            item.test_pointer, item.evidence_pointer, item.severity, max(0.0, min(1.0, item.confidence)),
            item.source_kind, item.source_ref, status, item.created_at or now, now)
        values = tuple(asdict(row).values())
        with self._connect() as db:
            db.execute("INSERT INTO regression_knowledge VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(knowledge_id) DO UPDATE SET updated_at=excluded.updated_at, status=excluded.status, confidence=excluded.confidence, test_pointer=excluded.test_pointer, evidence_pointer=excluded.evidence_pointer", values)
        return row.knowledge_id

    def retrieve(self, *, task_family: str, component: str = "", failure_signature: str = "", invariant: str = "", limit: int = 25) -> list[RegressionKnowledge]:
        with self._connect() as db:
            rows = db.execute("""SELECT * FROM regression_knowledge WHERE status='active' AND
                (task_family=? OR (?<>'' AND component=?) OR (?<>'' AND failure_signature=?) OR (?<>'' AND invariant=?))
                ORDER BY CASE WHEN failure_signature=? AND ?<>'' THEN 0 WHEN invariant=? AND ?<>'' THEN 1
                              WHEN component=? AND ?<>'' THEN 2 WHEN task_family=? THEN 3 ELSE 4 END,
                         confidence DESC, updated_at DESC, knowledge_id ASC LIMIT ?""",
                (task_family, component, component, failure_signature, failure_signature, invariant, invariant,
                 failure_signature, failure_signature, invariant, invariant, component, component, task_family, max(1, int(limit)))).fetchall()
        return [RegressionKnowledge(**dict(row)) for row in rows]

    def stats(self) -> dict[str, int]:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) AS total, SUM(status='active') AS active, SUM(status='pending') AS pending FROM regression_knowledge").fetchone()
        return {"total": int(row["total"] or 0), "active": int(row["active"] or 0), "pending": int(row["pending"] or 0)}
