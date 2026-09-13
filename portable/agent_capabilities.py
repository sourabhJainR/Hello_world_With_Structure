"""Unified operational capabilities for AER, inspired by Hermes Agent patterns.

This module is the single implementation for capability discovery/routing,
persistent memory, automation scheduling and output-quality checks. Public
compatibility modules delegate here so capabilities cannot drift into silos.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CAPABILITIES = (
    "web_search", "x_search", "terminal", "browser", "file", "vision", "image_generation",
    "tts", "todo", "memory", "session_search", "cronjob", "execute_code", "delegate_task",
    "clarify", "mcp", "skills", "background_processes", "provider_fallback",
)


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    requires_sandbox: bool = False
    requires_network: bool = False
    risk: str = "low"
    fallback: str | None = None


class CapabilityFabric:
    """Deterministic capability registry and policy planner."""

    def __init__(self, capabilities: Mapping[str, Capability]):
        self._capabilities = dict(capabilities)

    @classmethod
    def default(cls) -> "CapabilityFabric":
        return cls({
            "web_search": Capability("web_search", "web retrieval", requires_network=True, fallback=None),
            "x_search": Capability("x_search", "social/web search", requires_network=True, fallback="web_search"),
            "terminal": Capability("terminal", "repository command execution", requires_sandbox=True, risk="medium"),
            "browser": Capability("browser", "interactive browser automation", requires_network=True, risk="medium", fallback="web_search"),
            "file": Capability("file", "file inspection and mutation", requires_sandbox=True, risk="medium"),
            "vision": Capability("vision", "image understanding"),
            "image_generation": Capability("image_generation", "image generation", risk="medium"),
            "tts": Capability("tts", "speech synthesis"),
            "todo": Capability("todo", "dependency-aware task planning"),
            "memory": Capability("memory", "bounded persistent memory"),
            "session_search": Capability("session_search", "exact session recall"),
            "cronjob": Capability("cronjob", "durable scheduled tasks", risk="medium"),
            "execute_code": Capability("execute_code", "bounded code execution", requires_sandbox=True, risk="high"),
            "delegate_task": Capability("delegate_task", "parallel delegated work", risk="medium"),
            "clarify": Capability("clarify", "structured clarification"),
            "mcp": Capability("mcp", "external tool interoperability", risk="high"),
            "skills": Capability("skills", "progressive-disclosure skills"),
            "background_processes": Capability("background_processes", "durable background process lifecycle", risk="medium"),
            "provider_fallback": Capability("provider_fallback", "deterministic provider failover"),
        })

    def discover(self) -> dict[str, Capability]:
        return dict(sorted(self._capabilities.items()))

    def plan(self, requested: Iterable[str], *, network_allowed: bool, sandbox_available: bool = True) -> list[Capability]:
        planned: list[Capability] = []
        seen: set[str] = set()
        for name in requested:
            cap = self._capabilities.get(name)
            if cap is None:
                raise KeyError(f"unknown capability: {name}")
            if cap.requires_network and not network_allowed:
                if cap.fallback:
                    fallback = self._capabilities[cap.fallback]
                    if fallback.requires_network and not network_allowed:
                        planned.append(Capability("offline_search", "safe offline fallback"))
                    else:
                        planned.append(fallback)
                elif name == "web_search" or name == "x_search":
                    planned.append(Capability("offline_search", "safe offline fallback"))
                continue
            if cap.requires_sandbox and not sandbox_available:
                raise RuntimeError(f"capability requires sandbox: {name}")
            if cap.name not in seen:
                planned.append(cap); seen.add(cap.name)
        return planned


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*([^\s,;'\"]+)"),
    re.compile(r"-----BEGIN [A-Z0-9 ]+ PRIVATE KEY-----"),
)
_INJECTION_PATTERNS = (re.compile(r"(?i)ignore\s+(all|previous|prior)\s+instructions"),)


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=<redacted>" if m.lastindex else "<redacted>", text)
    return text


def _safe_text(text: str) -> str:
    if any(p.search(text) for p in _INJECTION_PATTERNS):
        raise ValueError("content rejected as prompt injection")
    return _redact(text)


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    category: str
    text: str
    intent_digest: str | None
    verified: bool
    confidence: float
    created_at: str


class PersistentMemory:
    """Bounded, intent-scoped memory with approval and full-text search."""

    def __init__(self, path: Path | str, *, require_write_approval: bool = True, max_chars: int = 32_000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.require_write_approval = require_write_approval
        self.max_chars = max_chars
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memory(
                    id TEXT PRIMARY KEY, category TEXT NOT NULL, text TEXT NOT NULL,
                    intent_digest TEXT, verified INTEGER NOT NULL, confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_text ON memory(category, text, COALESCE(intent_digest, ''));
            """)

    def remember(self, category: str, text: str, *, intent_digest: str | None = None, approved: bool = False, verified: bool = False, confidence: float = 0.0) -> MemoryRecord | None:
        cleaned = _safe_text(text)
        if self.require_write_approval and not approved:
            return None
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        with sqlite3.connect(self.path) as conn:
            existing = conn.execute("SELECT id,category,text,intent_digest,verified,confidence,created_at FROM memory WHERE category=? AND text=? AND COALESCE(intent_digest,'')=COALESCE(?, '')", (category, cleaned, intent_digest)).fetchone()
            if existing:
                return MemoryRecord(existing[0], existing[1], existing[2], existing[3], bool(existing[4]), float(existing[5]), existing[6])
            used = conn.execute("SELECT COALESCE(SUM(length(text)),0) FROM memory").fetchone()[0]
            if used + len(cleaned) > self.max_chars:
                raise ValueError("persistent memory capacity exceeded; consolidate before adding")
            record = MemoryRecord(uuid.uuid4().hex[:16], category, cleaned, intent_digest, bool(verified), confidence, datetime.now(timezone.utc).isoformat())
            conn.execute("INSERT INTO memory VALUES(?,?,?,?,?,?,?)", (record.id, record.category, record.text, record.intent_digest, int(record.verified), record.confidence, record.created_at))
            return record

    def search(self, query: str, *, intent_digest: str | None = None, limit: int = 20) -> list[MemoryRecord]:
        pattern = f"%{query}%"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT id,category,text,intent_digest,verified,confidence,created_at FROM memory WHERE text LIKE ? AND (? IS NULL OR intent_digest=?) ORDER BY created_at DESC LIMIT ?", (pattern, intent_digest, intent_digest, limit)).fetchall()
        return [MemoryRecord(row[0], row[1], row[2], row[3], bool(row[4]), float(row[5]), row[6]) for row in rows]

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class Schedule:
    id: str
    task: str
    interval_seconds: int
    max_attempts: int
    next_run: datetime
    enabled: bool = True

@dataclass(frozen=True)
class RunClaim:
    claim_id: str
    schedule_id: str
    claimed_at: datetime
    attempt: int

class AutomationScheduler:
    """SQLite-backed scheduler with claim-before-run and bounded retry state."""

    def __init__(self, path: Path | str):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY, task TEXT NOT NULL, interval_seconds INTEGER NOT NULL, max_attempts INTEGER NOT NULL, next_run TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, attempts INTEGER NOT NULL DEFAULT 0, claim_id TEXT);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL, started_at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL);
            """)

    def add(self, task: str, interval_seconds: int, *, max_attempts: int = 3, start: datetime | None = None) -> Schedule:
        if interval_seconds < 1 or max_attempts < 1: raise ValueError("interval and max_attempts must be positive")
        start = start or datetime.now(timezone.utc)
        schedule = Schedule(uuid.uuid4().hex[:16], task, interval_seconds, max_attempts, start)
        with sqlite3.connect(self.path) as conn: conn.execute("INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?)", (schedule.id, schedule.task, schedule.interval_seconds, schedule.max_attempts, schedule.next_run.isoformat(), 1, 0, None))
        return schedule

    def due(self, now: datetime | None = None) -> list[Schedule]:
        now = now or datetime.now(timezone.utc)
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT id,task,interval_seconds,max_attempts,next_run,enabled FROM schedules WHERE enabled=1 AND next_run<=? AND claim_id IS NULL ORDER BY next_run,id", (now.isoformat(),)).fetchall()
        return [Schedule(row[0], row[1], int(row[2]), int(row[3]), datetime.fromisoformat(row[4]), bool(row[5])) for row in rows]

    def claim(self, schedule_id: str, *, now: datetime | None = None) -> RunClaim | None:
        now = now or datetime.now(timezone.utc); claim_id = uuid.uuid4().hex[:16]
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT attempts,max_attempts,next_run,claim_id FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if not row or row[3] is not None or datetime.fromisoformat(row[2]) > now or int(row[0]) >= int(row[1]): return None
            attempt = int(row[0]) + 1
            conn.execute("UPDATE schedules SET attempts=?,claim_id=? WHERE id=?", (attempt, claim_id, schedule_id))
        return RunClaim(claim_id, schedule_id, now, attempt)

    def finish(self, claim: RunClaim, status: str, detail: str, *, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT interval_seconds,max_attempts,attempts FROM schedules WHERE id=? AND claim_id=?", (claim.schedule_id, claim.claim_id)).fetchone()
            if not row: raise KeyError("invalid or expired claim")
            if status == "retryable" and int(row[2]) < int(row[1]):
                next_run = now + timedelta(seconds=int(row[0])); enabled = 1
            else:
                next_run = now + timedelta(seconds=int(row[0])); enabled = 1
                if status not in {"success", "retryable"} or int(row[2]) >= int(row[1]): enabled = 0
            conn.execute("UPDATE schedules SET next_run=?,enabled=?,claim_id=NULL,attempts=? WHERE id=?", (next_run.isoformat(), enabled, 0 if status == "success" else int(row[2]), claim.schedule_id))
            conn.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (uuid.uuid4().hex[:16], claim.schedule_id, now.isoformat(), status, _redact(detail)))

    def recent_runs(self, schedule_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT id,schedule_id,started_at,status,detail FROM runs WHERE schedule_id=? ORDER BY started_at DESC LIMIT ?", (schedule_id, limit)).fetchall()
        return [dict(id=r[0], schedule_id=r[1], started_at=r[2], status=r[3], detail=r[4]) for r in rows]

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class QualityResult:
    status: str
    score: int
    findings: tuple[str, ...]

class OutputQualityGate:
    """Objective final-output gate: truthfulness, proof, scope and cleanliness."""

    def evaluate(self, report: Mapping[str, Any], *, acceptance_met: bool, verification_passed: bool, diff_clean: bool, evidence_count: int, scope_clean: bool) -> QualityResult:
        findings: list[str] = []
        score = 100
        if not acceptance_met: findings.append("acceptance criteria are not satisfied"); score -= 35
        if not verification_passed: findings.append("verification did not pass"); score -= 35
        if evidence_count < 1: findings.append("no evidence was supplied"); score -= 20
        if not diff_clean: findings.append("diff is not clean"); score -= 10
        if not scope_clean: findings.append("change scope is not clean"); score -= 10
        status = "ready" if not findings and score >= 90 else "blocked"
        return QualityResult(status, max(0, score), tuple(findings))


__all__ = ["CAPABILITIES", "Capability", "CapabilityFabric", "PersistentMemory", "MemoryRecord", "AutomationScheduler", "Schedule", "RunClaim", "OutputQualityGate", "QualityResult"]
