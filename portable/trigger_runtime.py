"""Durable event triggers that hand work to the existing AER orchestrator.

This is a coordination boundary, not an execution engine. It provides
idempotent event intake, single-owner claims, bounded retry/backoff and a
small dispatch adapter over the existing AutomationScheduler database.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from typing import Any, Callable, Mapping
import uuid

from .agent_capabilities import AutomationScheduler


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("trigger times must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class TriggerEvent:
    event_id: str
    kind: str
    payload: Mapping[str, Any]
    created_at: str
    available_at: str
    attempts: int
    max_attempts: int
    status: str
    last_detail: str = ""


@dataclass(frozen=True)
class TriggerClaim:
    event: TriggerEvent
    claim_id: str


class TriggerRuntime:
    """Persisted event inbox with at-most-one active claim per event."""

    def __init__(self, scheduler: AutomationScheduler, *, retry_delay_seconds: int = 5, max_events: int = 100_000) -> None:
        if not isinstance(scheduler, AutomationScheduler):
            raise TypeError("scheduler must be an AutomationScheduler")
        if retry_delay_seconds < 1 or max_events < 1:
            raise ValueError("retry delay and event bound must be positive")
        self.scheduler = scheduler
        self.retry_delay_seconds = retry_delay_seconds
        self.max_events = max_events
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.scheduler.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS trigger_events(
                    event_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    claim_id TEXT,
                    last_detail TEXT NOT NULL DEFAULT '')"""
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(trigger_events)")}
            if "last_detail" not in columns:
                db.execute("ALTER TABLE trigger_events ADD COLUMN last_detail TEXT NOT NULL DEFAULT ''")
            db.execute("CREATE INDEX IF NOT EXISTS idx_trigger_due ON trigger_events(status, available_at, event_id)")

    @staticmethod
    def _select_sql() -> str:
        return "SELECT event_id,kind,payload,created_at,available_at,attempts,max_attempts,status,last_detail FROM trigger_events"

    def emit(self, kind: str, payload: Mapping[str, Any], *, event_id: str | None = None,
             max_attempts: int = 3, not_before: datetime | None = None) -> TriggerEvent:
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("event kind is required")
        if not isinstance(payload, Mapping):
            raise TypeError("event payload must be a mapping")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        try:
            clean_payload = json.loads(json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        except (TypeError, ValueError) as exc:
            raise TypeError("event payload must be JSON-compatible") from exc
        event_id = event_id or uuid.uuid4().hex
        now = _utc()
        available = _aware(not_before) if not_before is not None else now
        payload_json = json.dumps(clean_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(self._select_sql() + " WHERE event_id=?", (event_id,)).fetchone()
            if row:
                existing = self._event(row)
                if existing.kind != kind.strip() or json.dumps(existing.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) != payload_json:
                    raise ValueError("event_id already exists with different content")
                return existing
            count = db.execute("SELECT COUNT(*) FROM trigger_events").fetchone()[0]
            if count >= self.max_events:
                raise ValueError("trigger event budget exceeded")
            db.execute("INSERT INTO trigger_events VALUES(?,?,?,?,?,?,?,?,NULL,'')", (event_id, kind.strip(), payload_json, now.isoformat(), available.isoformat(), 0, max_attempts, "pending"))
        return TriggerEvent(event_id, kind.strip(), clean_payload, now.isoformat(), available.isoformat(), 0, max_attempts, "pending")

    @staticmethod
    def _event(row) -> TriggerEvent:
        return TriggerEvent(row[0], row[1], json.loads(row[2]), row[3], row[4], int(row[5]), int(row[6]), row[7], row[8] or "")

    def due(self, *, now: datetime | None = None, limit: int = 20) -> tuple[TriggerEvent, ...]:
        if limit < 1:
            return ()
        now = _aware(now) if now is not None else _utc()
        with self._connect() as db:
            rows = db.execute(self._select_sql() + " WHERE status='pending' AND available_at<=? ORDER BY available_at,event_id LIMIT ?", (now.isoformat(), limit)).fetchall()
        return tuple(self._event(row) for row in rows)

    def claim(self, event_id: str, *, now: datetime | None = None) -> TriggerClaim | None:
        now = _aware(now) if now is not None else _utc()
        claim_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(self._select_sql() + " WHERE event_id=?", (event_id,)).fetchone()
            if not row or row[7] != "pending" or datetime.fromisoformat(row[4]) > now or int(row[5]) >= int(row[6]):
                return None
            updated = db.execute("UPDATE trigger_events SET status='claimed',claim_id=?,attempts=attempts+1 WHERE event_id=? AND status='pending' AND claim_id IS NULL", (claim_id, event_id)).rowcount
            if updated != 1:
                return None
            claimed = db.execute(self._select_sql() + " WHERE event_id=?", (event_id,)).fetchone()
        return TriggerClaim(self._event(claimed), claim_id)

    def complete(self, event_id: str, claim_id: str, status: str, detail: str = "", *, now: datetime | None = None) -> None:
        if status not in {"success", "retryable", "failed", "cancelled"}:
            raise ValueError("invalid trigger completion status")
        now = _aware(now) if now is not None else _utc()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT attempts,max_attempts,status,claim_id FROM trigger_events WHERE event_id=?", (event_id,)).fetchone()
            if not row or row[2] != "claimed" or row[3] != claim_id:
                raise KeyError("invalid trigger claim")
            attempts, max_attempts = int(row[0]), int(row[1])
            if status == "retryable" and attempts < max_attempts:
                available = now + timedelta(seconds=self.retry_delay_seconds * (2 ** max(0, attempts - 1)))
                db.execute("UPDATE trigger_events SET status='pending',claim_id=NULL,available_at=?,last_detail=? WHERE event_id=?", (available.isoformat(), detail[:2000], event_id))
            else:
                terminal = "success" if status == "success" else "cancelled" if status == "cancelled" else "failed"
                db.execute("UPDATE trigger_events SET status=?,claim_id=NULL,available_at=?,last_detail=? WHERE event_id=?", (terminal, now.isoformat(), detail[:2000], event_id))

    def dispatch_due(self, handler: Callable[[TriggerEvent], Any], *, now: datetime | None = None, limit: int = 20) -> list[Any]:
        if not callable(handler):
            raise TypeError("handler must be callable")
        results: list[Any] = []
        effective_now = _aware(now) if now is not None else _utc()
        for event in self.due(now=effective_now, limit=limit):
            claim = self.claim(event.event_id, now=effective_now)
            if claim is None:
                continue
            try:
                result = handler(claim.event)
            except Exception as exc:
                self.complete(claim.event.event_id, claim.claim_id, "retryable", str(exc), now=effective_now)
                continue
            self.complete(claim.event.event_id, claim.claim_id, "success", now=effective_now)
            results.append(result)
        return results


__all__ = ["TriggerClaim", "TriggerEvent", "TriggerRuntime"]
