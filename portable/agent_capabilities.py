"""Unified, provider-neutral agent capabilities for AER.

The module is deliberately stdlib-only and owns task-facing capability semantics:
provider adapters, bounded memory, session recall, skills, delegation receipts,
background jobs, scheduling, and final output-quality checks. AER policy,
sandboxing, verification and promotion remain authoritative elsewhere.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


CAPABILITIES = (
    "web_search", "x_search", "terminal", "browser", "file", "vision",
    "image_generation", "tts", "todo", "memory", "session_search",
    "cronjob", "execute_code", "delegate_task", "clarify", "mcp",
    "skills", "background_processes", "provider_fallback",
)

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*([^\s,;'\"]+)")
_INJECTION = re.compile(r"(?i)ignore\s+(all|previous|prior)\s+instructions")


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}=<redacted>", text)


def sanitize_untrusted(text: str) -> str:
    if _INJECTION.search(text):
        raise ValueError("untrusted content rejected: prompt-injection pattern")
    return redact(text)


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    risk: str = "low"
    requires_network: bool = False
    requires_sandbox: bool = False
    fallback: str | None = None


class CapabilityFabric:
    def __init__(self, capabilities: Mapping[str, Capability] | None = None) -> None:
        self._caps = dict(capabilities or self.default_catalog())

    @staticmethod
    def default_catalog() -> dict[str, Capability]:
        return {
            "web_search": Capability("web_search", "web retrieval", requires_network=True),
            "x_search": Capability("x_search", "social search", requires_network=True, fallback="web_search"),
            "terminal": Capability("terminal", "repository command execution", "medium", requires_sandbox=True),
            "browser": Capability("browser", "browser automation", "medium", requires_network=True, fallback="web_search"),
            "file": Capability("file", "repository file access", "medium", requires_sandbox=True),
            "vision": Capability("vision", "image understanding"),
            "image_generation": Capability("image_generation", "image generation", "medium"),
            "tts": Capability("tts", "speech synthesis"),
            "todo": Capability("todo", "dependency-aware task planning"),
            "memory": Capability("memory", "durable project memory"),
            "session_search": Capability("session_search", "cross-session recall"),
            "cronjob": Capability("cronjob", "durable scheduled automation", "medium"),
            "execute_code": Capability("execute_code", "bounded code execution", "high", requires_sandbox=True),
            "delegate_task": Capability("delegate_task", "bounded parallel delegation", "medium"),
            "clarify": Capability("clarify", "structured clarification"),
            "mcp": Capability("mcp", "external tool interoperability", "high"),
            "skills": Capability("skills", "progressive-disclosure procedures"),
            "background_processes": Capability("background_processes", "durable background work", "medium"),
            "provider_fallback": Capability("provider_fallback", "provider failover"),
        }

    def discover(self) -> dict[str, Capability]:
        return dict(sorted(self._caps.items()))

    def plan(self, requested: Iterable[str], *, network_allowed: bool, sandbox_available: bool = True,
             max_risk: str = "high") -> list[Capability]:
        if max_risk not in _RISK_ORDER:
            raise ValueError("invalid max_risk")
        result: list[Capability] = []
        seen: set[str] = set()
        for name in requested:
            cap = self._caps.get(name)
            if cap is None:
                raise KeyError(f"unknown capability: {name}")
            if _RISK_ORDER[cap.risk] > _RISK_ORDER[max_risk]:
                raise PermissionError(f"capability exceeds risk budget: {name}")
            if cap.requires_sandbox and not sandbox_available:
                raise PermissionError(f"sandbox required: {name}")
            selected = cap
            if cap.requires_network and not network_allowed:
                if not cap.fallback:
                    raise RuntimeError(f"network required and no safe fallback: {name}")
                selected = self._caps[cap.fallback]
            if selected.name not in seen:
                result.append(selected)
                seen.add(selected.name)
        return result


@dataclass(frozen=True)
class ProviderAdapter:
    name: str
    capabilities: frozenset[str]
    priority: int = 0
    enabled: bool = True


class ProviderAdapterRegistry:
    """Deterministic provider selection without owning provider execution."""
    def __init__(self, adapters: Sequence[ProviderAdapter] = ()) -> None:
        self._adapters = list(adapters)

    def register(self, adapter: ProviderAdapter) -> None:
        self._adapters = [a for a in self._adapters if a.name != adapter.name]
        self._adapters.append(adapter)

    def resolve(self, required: Iterable[str], preferred: Sequence[str] = ()) -> ProviderAdapter:
        required_set = set(required)
        preferred_rank = {name: i for i, name in enumerate(preferred)}
        candidates = [a for a in self._adapters if a.enabled and required_set.issubset(a.capabilities)]
        if not candidates:
            raise LookupError(f"no provider supports: {sorted(required_set)}")
        return sorted(candidates, key=lambda a: (preferred_rank.get(a.name, 10_000), -a.priority, a.name))[0]


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    project: str
    category: str
    text: str
    intent_digest: str | None
    confidence: float
    verified: bool
    created_at: str


class PersistentMemory:
    """SQLite WAL + FTS5 memory with redaction, scoping and approval gates."""
    def __init__(self, path: Path | str, *, max_chars: int = 100_000, require_approval: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_chars = max_chars
        self.require_approval = require_approval
        self._lock = threading.RLock()
        with self._connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS memory(
              id TEXT PRIMARY KEY, project TEXT NOT NULL, category TEXT NOT NULL,
              text TEXT NOT NULL, intent_digest TEXT, confidence REAL NOT NULL,
              verified INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(id UNINDEXED, text, category, project, content='');
            CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(project, intent_digest, created_at);
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def remember(self, project: str, category: str, text: str, *, intent_digest: str | None = None,
                 confidence: float = 0.0, verified: bool = False, approved: bool = False) -> MemoryRecord | None:
        if self.require_approval and not approved:
            return None
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        clean = sanitize_untrusted(text)
        with self._lock, self._connect() as db:
            used = db.execute("SELECT COALESCE(SUM(length(text)),0) FROM memory WHERE project=?", (project,)).fetchone()[0]
            if used + len(clean) > self.max_chars:
                raise ValueError("memory budget exceeded; consolidate or remove stale memories")
            duplicate = db.execute("SELECT id,project,category,text,intent_digest,confidence,verified,created_at FROM memory WHERE project=? AND category=? AND text=? AND COALESCE(intent_digest,'')=COALESCE(?, '')", (project, category, clean, intent_digest)).fetchone()
            if duplicate:
                return self._record(duplicate)
            record = MemoryRecord(uuid.uuid4().hex, project, category, clean, intent_digest, confidence, verified, _utc().isoformat())
            db.execute("INSERT INTO memory VALUES(?,?,?,?,?,?,?,?)", (record.id, record.project, record.category, record.text, record.intent_digest, record.confidence, int(record.verified), record.created_at))
            db.execute("INSERT INTO memory_fts(rowid,id,text,category,project) VALUES((SELECT rowid FROM memory WHERE id=?),?,?,?,?)", (record.id, record.id, record.text, record.category, record.project))
            return record

    @staticmethod
    def _record(row: Sequence[Any]) -> MemoryRecord:
        return MemoryRecord(row[0], row[1], row[2], row[3], row[4], float(row[5]), bool(row[6]), row[7])

    def search(self, project: str, query: str, *, intent_digest: str | None = None, limit: int = 20) -> list[MemoryRecord]:
        if not query.strip():
            return []
        terms = " ".join(re.findall(r"[A-Za-z0-9_]+", query))
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT m.id,m.project,m.category,m.text,m.intent_digest,m.confidence,m.verified,m.created_at
                FROM memory m JOIN memory_fts f ON f.id=m.id
                WHERE m.project=? AND f MATCH ? AND (? IS NULL OR m.intent_digest=?)
                ORDER BY m.verified DESC,m.confidence DESC,m.created_at DESC LIMIT ?""", (project, terms, intent_digest, intent_digest, limit)).fetchall()
        return [self._record(r) for r in rows]


@dataclass(frozen=True)
class DelegationReceipt:
    id: str
    task_id: str
    status: str
    started_at: str
    completed_at: str | None
    result: str | None
    error: str | None


class DelegationPool:
    def __init__(self, max_workers: int = 4) -> None:
        if not 1 <= max_workers <= 16:
            raise ValueError("max_workers must be 1..16")
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="aer-agent")

    def submit(self, task_id: str, fn: Callable[[], Any]) -> tuple[DelegationReceipt, Future[Any]]:
        receipt = DelegationReceipt(uuid.uuid4().hex, task_id, "running", _utc().isoformat(), None, None, None)
        def wrapped() -> Any:
            return fn()
        return receipt, self._pool.submit(wrapped)

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)


@dataclass(frozen=True)
class Schedule:
    id: str
    task: str
    interval_seconds: int
    max_attempts: int
    next_run: str
    enabled: bool
    attempts: int


class AutomationScheduler:
    """Claim-before-run scheduler. Execution is always handed back to AER."""
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self._lock = threading.RLock()
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
              CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,task TEXT NOT NULL,interval_seconds INTEGER NOT NULL,max_attempts INTEGER NOT NULL,next_run TEXT NOT NULL,enabled INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,claim TEXT);
              CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,schedule_id TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,status TEXT,detail TEXT);
            """)

    def add(self, task: str, interval_seconds: int, *, max_attempts: int = 3, start: datetime | None = None) -> Schedule:
        if interval_seconds < 1 or max_attempts < 1:
            raise ValueError("interval_seconds and max_attempts must be positive")
        when = start or _utc(); sid = uuid.uuid4().hex
        with self._lock, sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO schedules VALUES(?,?,?,?,?,?,?,NULL)", (sid, sanitize_untrusted(task), interval_seconds, max_attempts, when.isoformat(), 1, 0))
        return Schedule(sid, task, interval_seconds, max_attempts, when.isoformat(), True, 0)

    def due(self, now: datetime | None = None) -> list[Schedule]:
        now = now or _utc()
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,task,interval_seconds,max_attempts,next_run,enabled,attempts FROM schedules WHERE enabled=1 AND claim IS NULL AND next_run<=? ORDER BY next_run,id", (now.isoformat(),)).fetchall()
        return [Schedule(r[0],r[1],int(r[2]),int(r[3]),r[4],bool(r[5]),int(r[6])) for r in rows]

    def claim(self, schedule_id: str, *, now: datetime | None = None) -> str | None:
        now = now or _utc(); claim = uuid.uuid4().hex
        with self._lock, sqlite3.connect(self.path) as db:
            row = db.execute("SELECT next_run,enabled,attempts,max_attempts,claim FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if not row or not row[1] or row[4] or datetime.fromisoformat(row[0]) > now or int(row[2]) >= int(row[3]):
                return None
            updated = db.execute("UPDATE schedules SET attempts=attempts+1,claim=? WHERE id=? AND claim IS NULL AND enabled=1", (claim,schedule_id)).rowcount
            return claim if updated == 1 else None

    def finish(self, schedule_id: str, claim: str, status: str, detail: str = "", *, now: datetime | None = None) -> None:
        if status not in {"success", "retryable", "failed", "cancelled"}:
            raise ValueError("invalid run status")
        now = now or _utc()
        with self._lock, sqlite3.connect(self.path) as db:
            row = db.execute("SELECT interval_seconds,max_attempts,attempts FROM schedules WHERE id=? AND claim=?", (schedule_id,claim)).fetchone()
            if not row:
                raise KeyError("invalid scheduler claim")
            exhausted = int(row[2]) >= int(row[1])
            enabled = int(status == "success" or (status == "retryable" and not exhausted))
            next_run = now + timedelta(seconds=int(row[0]))
            db.execute("UPDATE schedules SET claim=NULL,enabled=?,next_run=?,attempts=? WHERE id=?", (enabled,next_run.isoformat(),0 if status == "success" else int(row[2]),schedule_id))
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)", (uuid.uuid4().hex,schedule_id,now.isoformat(),now.isoformat(),status,redact(detail)))


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    requires: frozenset[str] = frozenset()


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not skill.name.strip() or not skill.instructions.strip():
            raise ValueError("skill name and instructions are required")
        self._skills[skill.name] = skill

    def discover(self, query: str = "") -> list[Skill]:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        def score(s: Skill) -> tuple[int, str]:
            words = set(re.findall(r"[a-z0-9]+", (s.name + " " + s.description).lower()))
            return (len(tokens & words), s.name)
        return sorted(self._skills.values(), key=score, reverse=True)

    def load(self, name: str, available: Iterable[str]) -> Skill:
        skill = self._skills[name]
        missing = skill.requires - set(available)
        if missing:
            raise PermissionError(f"skill prerequisites unavailable: {sorted(missing)}")
        return skill


@dataclass(frozen=True)
class QualityResult:
    status: str
    score: int
    findings: tuple[str, ...]


class OutputQualityGate:
    def evaluate(self, *, acceptance_met: bool, verification_passed: bool, evidence_count: int,
                 diff_clean: bool, scope_clean: bool, unresolved: int = 0) -> QualityResult:
        findings: list[str] = []; score = 100
        checks = ((acceptance_met,35,"acceptance criteria not satisfied"),(verification_passed,35,"verification did not pass"),(evidence_count > 0,15,"no evidence supplied"),(diff_clean,10,"diff is not clean"),(scope_clean,5,"scope is not clean"),(unresolved == 0,5,"unresolved findings remain"))
        for ok, penalty, finding in checks:
            if not ok: findings.append(finding); score -= penalty
        return QualityResult("ready" if not findings else "blocked", max(0, score), tuple(findings))


__all__ = [
    "CAPABILITIES", "Capability", "CapabilityFabric", "ProviderAdapter", "ProviderAdapterRegistry",
    "MemoryRecord", "PersistentMemory", "DelegationReceipt", "DelegationPool", "Schedule",
    "AutomationScheduler", "Skill", "SkillRegistry", "QualityResult", "OutputQualityGate",
    "redact", "sanitize_untrusted",
]
