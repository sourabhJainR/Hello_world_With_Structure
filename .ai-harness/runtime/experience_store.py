#!/usr/bin/env python3
"""Durable, indexed experience store for the self-improving coding loop."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Experience:
    task_id: str
    task_class: str
    strategy: str
    success: bool
    accepted: bool
    verification_passed: bool
    retries: int = 0
    regressions: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    safety_passed: bool = True
    evidence_score: float = 1.0
    environment_fingerprint: str = ""
    policy_id: str = ""
    transfer_key: str = ""
    failure_class: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        payload = {"task_id": self.task_id, "task_class": self.task_class,
                   "strategy": self.strategy, "timestamp": self.timestamp}
        return "exp-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


class ExperienceStore:
    """Local SQLite store with atomic writes and indexed task-family queries."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    task_id TEXT NOT NULL,
                    task_class TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    accepted INTEGER NOT NULL,
                    verification_passed INTEGER NOT NULL,
                    retries INTEGER NOT NULL,
                    regressions INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    latency_ms REAL NOT NULL,
                    safety_passed INTEGER NOT NULL,
                    evidence_score REAL NOT NULL,
                    environment_fingerprint TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    transfer_key TEXT NOT NULL,
                    failure_class TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_experience_class ON experiences(task_class, timestamp);
                CREATE INDEX IF NOT EXISTS idx_experience_strategy ON experiences(task_class, strategy, timestamp);
                CREATE INDEX IF NOT EXISTS idx_experience_policy ON experiences(policy_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_experience_transfer ON experiences(transfer_key, timestamp);
            """)

    def record(self, experience: Experience) -> str:
        with self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO experiences
                (id,schema_version,task_id,task_class,strategy,success,accepted,
                 verification_passed,retries,regressions,cost,latency_ms,safety_passed,
                 evidence_score,environment_fingerprint,policy_id,transfer_key,
                 failure_class,timestamp,metadata_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (experience.id, SCHEMA_VERSION, experience.task_id, experience.task_class,
                 experience.strategy, int(experience.success), int(experience.accepted),
                 int(experience.verification_passed), experience.retries, experience.regressions,
                 experience.cost, experience.latency_ms, int(experience.safety_passed),
                 max(0.0, min(1.0, experience.evidence_score)), experience.environment_fingerprint,
                 experience.policy_id, experience.transfer_key, experience.failure_class,
                 experience.timestamp, json.dumps(experience.metadata, sort_keys=True)),
            )
        return experience.id

    def record_many(self, experiences: Iterable[Experience]) -> int:
        count = 0
        for experience in experiences:
            self.record(experience)
            count += 1
        return count

    def recent(self, limit: int = 500) -> list[Experience]:
        return self._query("SELECT * FROM experiences ORDER BY timestamp DESC, id DESC LIMIT ?", (self._limit(limit),))

    def by_task_class(self, task_class: str, limit: int = 500) -> list[Experience]:
        return self._query("SELECT * FROM experiences WHERE task_class=? ORDER BY timestamp DESC, id DESC LIMIT ?", (task_class, self._limit(limit)))

    def by_strategy(self, task_class: str, strategy: str, limit: int = 500) -> list[Experience]:
        return self._query("SELECT * FROM experiences WHERE task_class=? AND strategy=? ORDER BY timestamp DESC, id DESC LIMIT ?", (task_class, strategy, self._limit(limit)))

    def count(self, task_class: str | None = None) -> int:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM experiences" if task_class is None else "SELECT COUNT(*) AS n FROM experiences WHERE task_class=?", () if task_class is None else (task_class,)).fetchone()
            return int(row["n"])

    @staticmethod
    def _limit(limit: int) -> int:
        return max(1, min(10000, int(limit)))

    def _query(self, sql: str, params: tuple[Any, ...]) -> list[Experience]:
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [Experience(
            task_id=row["task_id"], task_class=row["task_class"], strategy=row["strategy"],
            success=bool(row["success"]), accepted=bool(row["accepted"]),
            verification_passed=bool(row["verification_passed"]), retries=int(row["retries"]),
            regressions=int(row["regressions"]), cost=float(row["cost"]), latency_ms=float(row["latency_ms"]),
            safety_passed=bool(row["safety_passed"]), evidence_score=float(row["evidence_score"]),
            environment_fingerprint=row["environment_fingerprint"], policy_id=row["policy_id"],
            transfer_key=row["transfer_key"], failure_class=row["failure_class"], timestamp=int(row["timestamp"]),
            metadata=json.loads(row["metadata_json"] or "{}")) for row in rows]

    def summary(self, task_class: str | None = None) -> dict[str, Any]:
        rows = self.recent(10000) if task_class is None else self.by_task_class(task_class, 10000)
        if not rows:
            return {"count": 0, "success_rate": 0.0, "acceptance_rate": 0.0, "verification_rate": 0.0, "regression_rate": 0.0}
        n = len(rows)
        return {"count": n, "success_rate": sum(x.success for x in rows) / n,
                "acceptance_rate": sum(x.accepted for x in rows) / n,
                "verification_rate": sum(x.verification_passed for x in rows) / n,
                "regression_rate": sum(x.regressions > 0 for x in rows) / n,
                "avg_retries": sum(x.retries for x in rows) / n,
                "avg_cost": sum(x.cost for x in rows) / n,
                "avg_latency_ms": sum(x.latency_ms for x in rows) / n}


def experience_from_mapping(value: dict[str, Any]) -> Experience:
    """Compatibility adapter for snapshots/events produced by older runtime versions."""
    return Experience(
        task_id=str(value.get("task_id", value.get("turn_id", "unknown"))),
        task_class=str(value.get("task_class", value.get("mode", "implement"))),
        strategy=str(value.get("strategy", "unknown")), success=bool(value.get("success", False)),
        accepted=bool(value.get("accepted", False)),
        verification_passed=bool(value.get("verification_passed", value.get("verification_score", 0) >= .75)),
        retries=int(value.get("retries", 0) or 0), regressions=int(value.get("regressions", 0) or 0),
        cost=float(value.get("cost", value.get("token_cost", 0)) or 0), latency_ms=float(value.get("latency_ms", 0) or 0),
        safety_passed=bool(value.get("safety_passed", True)), evidence_score=float(value.get("evidence_score", 1.0) or 0),
        environment_fingerprint=str(value.get("environment_fingerprint", "")), policy_id=str(value.get("policy_id", "")),
        transfer_key=str(value.get("transfer_key", value.get("task_class", ""))),
        failure_class=str(value.get("failure_class", "")), timestamp=int(value.get("timestamp", time.time())),
        metadata=dict(value.get("metadata", {})) if isinstance(value.get("metadata"), dict) else {})
