"""Deterministic execution lifecycle and append-only provenance ledger."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Mapping


class ExecutionState(str, Enum):
    CREATED = "created"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    ESCALATED = "escalated"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


TERMINAL_STATES = {ExecutionState.PASSED, ExecutionState.FAILED, ExecutionState.BLOCKED}

_ALLOWED = {
    ExecutionState.CREATED: {ExecutionState.PLANNED, ExecutionState.BLOCKED},
    ExecutionState.PLANNED: {ExecutionState.EXECUTING, ExecutionState.BLOCKED},
    ExecutionState.EXECUTING: {ExecutionState.VERIFYING, ExecutionState.FAILED, ExecutionState.BLOCKED},
    ExecutionState.VERIFYING: {ExecutionState.PASSED, ExecutionState.FAILED, ExecutionState.REPAIRING, ExecutionState.BLOCKED},
    ExecutionState.REPAIRING: {ExecutionState.EXECUTING, ExecutionState.VERIFYING, ExecutionState.ESCALATED, ExecutionState.BLOCKED},
    ExecutionState.ESCALATED: {ExecutionState.BLOCKED, ExecutionState.PLANNED},
    ExecutionState.PASSED: set(),
    ExecutionState.FAILED: set(),
    ExecutionState.BLOCKED: set(),
}


@dataclass(frozen=True)
class ExecutionEvent:
    sequence: int
    state: str
    event: str
    detail: str = ""
    parent_event_id: str = ""
    event_id: str = field(init=False)

    def __post_init__(self) -> None:
        payload = {"sequence": self.sequence, "state": self.state, "event": self.event, "detail": self.detail, "parent_event_id": self.parent_event_id}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        object.__setattr__(self, "event_id", hashlib.sha256(encoded).hexdigest()[:16])

    def as_dict(self) -> dict[str, str | int]:
        return {"sequence": self.sequence, "state": self.state, "event": self.event, "detail": self.detail, "parent_event_id": self.parent_event_id, "event_id": self.event_id}


@dataclass
class ProvenanceLedger:
    events: list[ExecutionEvent] = field(default_factory=list)

    def append(self, state: ExecutionState | str, event: str, detail: str = "") -> ExecutionEvent:
        if not event.strip():
            raise ValueError("event must not be empty")
        state_value = state.value if isinstance(state, ExecutionState) else str(state)
        parent = self.events[-1].event_id if self.events else ""
        item = ExecutionEvent(len(self.events) + 1, state_value, event, detail, parent)
        self.events.append(item)
        return item

    def as_dict(self) -> dict[str, list[dict]]:
        return {"events": [e.as_dict() for e in self.events]}


@dataclass
class ExecutionLifecycle:
    state: ExecutionState = ExecutionState.CREATED
    repair_attempts: int = 0
    max_repairs: int = 2
    ledger: ProvenanceLedger = field(default_factory=ProvenanceLedger)

    def __post_init__(self) -> None:
        if self.max_repairs < 0:
            raise ValueError("max_repairs must be non-negative")
        self.ledger.append(self.state, "execution-created")

    def transition(self, next_state: ExecutionState, reason: str = "") -> ExecutionEvent:
        if self.state in TERMINAL_STATES:
            raise RuntimeError(f"terminal state {self.state.value} cannot transition")
        if next_state not in _ALLOWED[self.state]:
            raise ValueError(f"invalid transition: {self.state.value} -> {next_state.value}")
        if next_state == ExecutionState.REPAIRING:
            if self.repair_attempts >= self.max_repairs:
                self.state = ExecutionState.ESCALATED
                return self.ledger.append(self.state, "repair-limit-reached", reason)
            self.repair_attempts += 1
        self.state = next_state
        return self.ledger.append(self.state, f"state-transition:{next_state.value}", reason)

    def request_repair(self, reason: str = "") -> ExecutionEvent:
        return self.transition(ExecutionState.REPAIRING, reason)

    def escalate(self, reason: str = "") -> ExecutionEvent:
        if self.state in TERMINAL_STATES:
            raise RuntimeError(f"terminal state {self.state.value} cannot escalate")
        self.state = ExecutionState.ESCALATED
        return self.ledger.append(self.state, "escalated", reason)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def snapshot(self) -> dict[str, object]:
        return {"state": self.state.value, "repair_attempts": self.repair_attempts, "max_repairs": self.max_repairs, "terminal": self.terminal, "ledger": self.ledger.as_dict()}


def validate_transition_graph(graph: Mapping[str, set[str]] | None = None) -> None:
    graph = graph or {k.value: {s.value for s in v} for k, v in _ALLOWED.items()}
    terminal_values = {s.value for s in TERMINAL_STATES}
    for source, destinations in graph.items():
        if source in terminal_values and destinations:
            raise ValueError(f"terminal state has outgoing transitions: {source}")
        if not isinstance(destinations, set):
            raise ValueError(f"destinations for {source} must be a set")
