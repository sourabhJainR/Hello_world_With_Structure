#!/usr/bin/env python3
"""Runtime Context Broker: demand-driven, scored, bounded context discovery.

The broker keeps context as retrievable candidates rather than active prompt
state. Candidates are scored against the current task/phase/question, selected
under a hard budget, materialized just before use, and released after the phase.
It stores only compact provenance/decision metadata, never raw context.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Any
import hashlib
import re
import time


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    context_id: str
    kind: str
    reason: str
    loader: Callable[[], str]
    relevance: float = 0.0
    confidence: float = 0.8
    freshness: float = 0.8
    risk: float = 0.0
    cost: int = 1
    required: bool = False
    phase: str = "*"

    def score(self, query: str, phase: str) -> float:
        words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", query.lower()))
        id_words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (self.context_id + " " + self.kind).lower()))
        lexical = len(words & id_words) / max(1, len(words))
        phase_bonus = 0.25 if self.phase in {"*", phase} else -0.25
        return (0.45 * max(0.0, min(1.0, self.relevance))
                + 0.15 * max(0.0, min(1.0, self.confidence))
                + 0.10 * max(0.0, min(1.0, self.freshness))
                + 0.15 * lexical + 0.15 * max(0.0, min(1.0, self.risk))
                + phase_bonus)


@dataclass(frozen=True, slots=True)
class ContextLease:
    context_id: str
    kind: str
    text: str
    score: float
    reason: str
    acquired_at: float
    digest: str


class ContextBroker:
    """Demand-driven context lifecycle: discover -> score -> load -> release."""

    def __init__(self, *, budget_chars: int = 12000, max_items: int = 18) -> None:
        self.budget_chars = max(256, int(budget_chars))
        self.max_items = max(1, int(max_items))
        self._candidates: dict[str, ContextCandidate] = {}
        self._active: dict[str, ContextLease] = {}
        self._events: list[dict[str, Any]] = []

    def register(self, candidate: ContextCandidate) -> None:
        if candidate.cost < 0:
            raise ValueError("context candidate cost cannot be negative")
        self._candidates[candidate.context_id] = candidate

    def register_many(self, candidates: Iterable[ContextCandidate]) -> None:
        for candidate in candidates:
            self.register(candidate)

    def discover(self, query: str, *, phase: str = "", budget_chars: int | None = None, max_items: int | None = None) -> list[ContextLease]:
        """Select and materialize only the highest-value candidates for this decision."""
        budget = self.budget_chars if budget_chars is None else max(0, int(budget_chars))
        limit = self.max_items if max_items is None else max(1, int(max_items))
        ranked = sorted(self._candidates.values(), key=lambda c: (c.required, c.score(query, phase), c.context_id), reverse=True)
        leases: list[ContextLease] = []
        used = 0
        for candidate in ranked:
            if len(leases) >= limit:
                break
            if not candidate.required and candidate.phase not in {"*", phase}:
                continue
            text = str(candidate.loader() or "")
            size = len(text)
            if size == 0:
                continue
            if not candidate.required and used + size > budget:
                continue
            if candidate.required and size > budget - used:
                raise RuntimeError(f"required context exceeds broker budget: {candidate.context_id}")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            lease = ContextLease(candidate.context_id, candidate.kind, text, candidate.score(query, phase), candidate.reason, time.time(), digest)
            self._active[candidate.context_id] = lease
            leases.append(lease)
            used += size
        self._events.append({"event": "discover", "phase": phase, "query_digest": hashlib.sha256(query.encode()).hexdigest()[:16], "selected": [x.context_id for x in leases], "chars": used})
        return leases

    def release(self, context_ids: Iterable[str] | None = None) -> None:
        ids = list(self._active) if context_ids is None else list(context_ids)
        for context_id in ids:
            lease = self._active.pop(context_id, None)
            if lease:
                self._events.append({"event": "release", "context_id": context_id, "digest": lease.digest})

    def active(self) -> tuple[ContextLease, ...]:
        return tuple(self._active.values())

    def telemetry(self) -> dict[str, Any]:
        return {"candidates": len(self._candidates), "active": len(self._active), "events": list(self._events[-50:]), "budget_chars": self.budget_chars, "max_items": self.max_items}
