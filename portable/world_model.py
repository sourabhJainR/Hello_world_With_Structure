"""Durable, provenance-aware world-model primitives for AER.

The world model is a semantic layer over the existing canonical AER memory
SQLite database. It records observations and state facts without becoming a
second orchestration engine. Facts are append-only observations; current state
is derived deterministically from the latest observation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from typing import Any, Mapping

from .persistent_memory import PersistentMemory


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _props(value: str) -> dict[str, Any]:
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("world-model properties must decode to an object")
    return decoded


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class Observation:
    observation_id: str
    entity_id: str
    predicate: str
    value: Any
    source: str
    confidence: float = 1.0
    observed_at: str = ""
    evidence: tuple[str, ...] = ()
    properties: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name, value in (("observation_id", self.observation_id), ("entity_id", self.entity_id),
                            ("predicate", self.predicate), ("source", self.source)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.observed_at:
            object.__setattr__(self, "observed_at", _utc())
        else:
            object.__setattr__(self, "observed_at", _timestamp(self.observed_at))
        if self.properties is None:
            object.__setattr__(self, "properties", {})
        if not isinstance(self.properties, Mapping):
            raise TypeError("properties must be a mapping")
        try:
            json.dumps(self.value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            json.dumps(dict(self.properties), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        except (TypeError, ValueError) as exc:
            raise TypeError("value and properties must be JSON-compatible") from exc


@dataclass(frozen=True)
class WorldFact:
    entity_id: str
    predicate: str
    value: Any
    source: str
    confidence: float
    observed_at: str
    observation_id: str
    evidence: tuple[str, ...] = ()
    properties: Mapping[str, Any] | None = None


class WorldModel:
    """Bounded durable observations and deterministic current-state queries."""

    def __init__(self, memory: PersistentMemory, project: str, *, max_observations: int = 100_000) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if max_observations < 1:
            raise ValueError("max_observations must be positive")
        self.memory = memory
        self.project = project
        self.max_observations = max_observations
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.memory.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS world_observations(
                    project TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    observed_at TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    PRIMARY KEY(project, observation_id))"""
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_world_observation_fact ON world_observations(project, entity_id, predicate, observed_at, observation_id)")

    def observe(self, observation: Observation) -> Observation:
        value_json = json.dumps(observation.value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        evidence_json = json.dumps(sorted(set(observation.evidence)), separators=(",", ":"), ensure_ascii=True)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT entity_id,predicate,value,source,confidence,observed_at,evidence,properties FROM world_observations WHERE project=? AND observation_id=?",
                (self.project, observation.observation_id),
            ).fetchone()
            if existing:
                if existing != (observation.entity_id, observation.predicate, value_json, observation.source,
                                observation.confidence, observation.observed_at, evidence_json, _json(observation.properties)):
                    raise ValueError("observation_id already exists with different content")
                return observation
            count = db.execute("SELECT COUNT(*) FROM world_observations WHERE project=?", (self.project,)).fetchone()[0]
            if count >= self.max_observations:
                raise ValueError("world-model observation budget exceeded")
            db.execute(
                "INSERT INTO world_observations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (self.project, observation.observation_id, observation.entity_id, observation.predicate,
                 value_json, observation.source, observation.confidence, observation.observed_at,
                 evidence_json, _json(observation.properties)),
            )
        return observation

    def current(self, entity_id: str, predicate: str | None = None, *, limit: int = 100) -> tuple[WorldFact, ...]:
        if limit < 1:
            return ()
        params: list[Any] = [self.project, entity_id]
        clause = "project=? AND entity_id=?"
        if predicate is not None:
            clause += " AND predicate=?"
            params.append(predicate)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT entity_id,predicate,value,source,confidence,observed_at,observation_id,evidence,properties FROM world_observations WHERE {clause} ORDER BY predicate,observed_at DESC,observation_id DESC",
                tuple(params),
            ).fetchall()
        latest: dict[str, WorldFact] = {}
        for row in rows:
            fact = WorldFact(row[0], row[1], json.loads(row[2]), row[3], float(row[4]), row[5], row[6],
                             tuple(json.loads(row[7])), _props(row[8]))
            latest.setdefault(fact.predicate, fact)
            if len(latest) >= limit:
                break
        return tuple(latest.values())

    def history(self, entity_id: str, predicate: str | None = None, *, limit: int = 100) -> tuple[Observation, ...]:
        if limit < 1:
            return ()
        params: list[Any] = [self.project, entity_id]
        clause = "project=? AND entity_id=?"
        if predicate is not None:
            clause += " AND predicate=?"
            params.append(predicate)
        params.append(limit)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT observation_id,entity_id,predicate,value,source,confidence,observed_at,evidence,properties FROM world_observations WHERE {clause} ORDER BY observed_at DESC,observation_id DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        return tuple(Observation(row[0], row[1], row[2], json.loads(row[3]), row[4], float(row[5]), row[6],
                                  tuple(json.loads(row[7])), _props(row[8])) for row in rows)

    def digest(self) -> str:
        with self._connect() as db:
            rows = db.execute(
                "SELECT observation_id,entity_id,predicate,value,source,confidence,observed_at,evidence,properties FROM world_observations WHERE project=? ORDER BY observation_id",
                (self.project,),
            ).fetchall()
        return hashlib.sha256(_json({"project": self.project, "observations": rows}).encode("utf-8")).hexdigest()[:16]


__all__ = ["Observation", "WorldFact", "WorldModel"]
