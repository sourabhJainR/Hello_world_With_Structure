"""Small provider-neutral state graph runtime inspired by durable agent graphs.

AER deliberately does not depend on LangGraph. This module adopts the useful
architectural ideas: explicit state, reducer-based merges, conditional routing,
bounded retries, checkpoint-after-step durability, interrupts, and deterministic
execution traces. Model/provider/tool execution remains outside the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence


State = MutableMapping[str, Any]
Node = Callable[[Mapping[str, Any]], Mapping[str, Any]]
Router = Callable[[Mapping[str, Any]], str | Sequence[str]]
Reducer = Callable[[Any, Any], Any]
CheckpointStore = Callable[["Checkpoint"], None]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")


@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    step: int
    state: dict[str, Any]
    next_nodes: tuple[str, ...]
    trace: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphInterrupt(Exception):
    run_id: str
    step: int
    state: dict[str, Any]
    next_nodes: tuple[str, ...]
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True)
class GraphEvent:
    step: int
    node: str
    status: str
    attempts: int = 1
    detail: str = ""


@dataclass(frozen=True)
class GraphRun:
    run_id: str
    state: dict[str, Any]
    events: tuple[GraphEvent, ...]
    trace: tuple[str, ...]
    steps: int
    interrupted: bool = False

    @property
    def digest(self) -> str:
        payload = repr((self.run_id, self.state, self.trace, self.events)).encode("utf-8")
        return sha256(payload).hexdigest()[:16]

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "events": [event.__dict__ for event in self.events],
            "trace": list(self.trace),
            "steps": self.steps,
            "interrupted": self.interrupted,
            "digest": self.digest,
        }


class InMemoryCheckpointStore:
    """Minimal checkpoint store suitable for tests and host adapters."""

    def __init__(self) -> None:
        self._items: dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        self._items[checkpoint.run_id] = checkpoint

    def load(self, run_id: str) -> Checkpoint | None:
        return self._items.get(run_id)


class StateGraph:
    """Deterministic stateful graph executor.

    Nodes return partial state. Multiple nodes scheduled in the same superstep
    are evaluated against the same state snapshot and their updates are merged
    through declared reducers. This prevents accidental ordering dependence.
    """

    START = "__start__"
    END = "__end__"

    def __init__(self, *, reducers: Mapping[str, Reducer] | None = None) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, tuple[str, ...]] = {}
        self._routers: dict[str, Router] = {}
        self._reducers = dict(reducers or {})
        self._retry: dict[str, RetryPolicy] = {}
        self._before: set[str] = set()
        self._after: set[str] = set()

    def add_node(self, name: str, node: Node, *, retry_policy: RetryPolicy | None = None) -> "StateGraph":
        if not name.strip() or name in {self.START, self.END}:
            raise ValueError("invalid node name")
        if name in self._nodes:
            raise ValueError(f"duplicate node: {name}")
        self._nodes[name] = node
        if retry_policy:
            self._retry[name] = retry_policy
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        self._validate_target(target)
        self._edges[source] = self._edges.get(source, ()) + (target,)
        return self

    def add_conditional_edges(self, source: str, router: Router) -> "StateGraph":
        if source not in self._nodes:
            raise ValueError(f"unknown source node: {source}")
        self._routers[source] = router
        return self

    def interrupt_before(self, *nodes: str) -> "StateGraph":
        for node in nodes:
            self._validate_target(node, allow_end=False)
        self._before.update(nodes)
        return self

    def interrupt_after(self, *nodes: str) -> "StateGraph":
        for node in nodes:
            self._validate_target(node, allow_end=False)
        self._after.update(nodes)
        return self

    def compile(self) -> "CompiledStateGraph":
        if not self._nodes:
            raise ValueError("graph must contain at least one node")
        if self.START not in self._edges:
            raise ValueError("graph must define an entry edge from START")
        return CompiledStateGraph(self)

    def _validate_target(self, target: str, *, allow_end: bool = True) -> None:
        if target != self.END and target not in self._nodes:
            raise ValueError(f"unknown graph node: {target}")
        if not allow_end and target == self.END:
            raise ValueError("END is not a node")


class CompiledStateGraph:
    def __init__(self, graph: StateGraph) -> None:
        self._g = graph

    def invoke(
        self,
        state: Mapping[str, Any],
        *,
        run_id: str = "run",
        checkpoint: CheckpointStore | None = None,
        resume: bool = False,
        max_steps: int = 100,
    ) -> GraphRun:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        store = checkpoint
        existing = getattr(store, "load", lambda _run_id: None)(run_id) if resume and store else None
        current: dict[str, Any] = dict(existing.state if existing else state)
        next_nodes = list(existing.next_nodes if existing else self._g._edges[StateGraph.START])
        events: list[GraphEvent] = []
        trace = list(existing.trace if existing else ())
        step = existing.step if existing else 0

        while next_nodes:
            if step >= max_steps:
                raise RuntimeError(f"graph exceeded max_steps={max_steps}")
            step += 1
            snapshot = dict(current)
            updates: list[tuple[str, Mapping[str, Any], int]] = []
            for name in tuple(next_nodes):
                if name == StateGraph.END:
                    continue
                if name in self._g._before and not (existing and step == existing.step + 1):
                    cp = Checkpoint(run_id, step - 1, dict(current), tuple(next_nodes), tuple(trace))
                    if store:
                        store.save(cp)
                    raise GraphInterrupt(run_id, step - 1, dict(current), tuple(next_nodes), f"interrupted before {name}")
                output, attempts = self._run_node(name, snapshot)
                updates.append((name, output, attempts))

            for name, output, attempts in updates:
                self._merge(current, output)
                events.append(GraphEvent(step, name, "completed", attempts))
                trace.append(name)
                if name in self._g._after:
                    next_after = self._next(name, current)
                    cp = Checkpoint(run_id, step, dict(current), tuple(next_after), tuple(trace))
                    if store:
                        store.save(cp)
                    raise GraphInterrupt(run_id, step, dict(current), tuple(next_after), f"interrupted after {name}")

            next_set: list[str] = []
            for name, _output, _attempts in updates:
                next_set.extend(self._next(name, current))
            next_nodes = list(dict.fromkeys(next_set))
            if store:
                store.save(Checkpoint(run_id, step, dict(current), tuple(next_nodes), tuple(trace)))
            existing = None
            if StateGraph.END in next_nodes:
                next_nodes = []

        return GraphRun(run_id, dict(current), tuple(events), tuple(trace), step)

    def _run_node(self, name: str, state: Mapping[str, Any]) -> tuple[Mapping[str, Any], int]:
        policy = self._g._retry.get(name, RetryPolicy())
        last: Exception | None = None
        for attempt in range(1, policy.max_attempts + 1):
            try:
                output = self._g._nodes[name](dict(state))
                if not isinstance(output, Mapping):
                    raise TypeError(f"node {name} must return a mapping")
                return output, attempt
            except Exception as exc:  # retry is bounded; final exception is preserved
                last = exc
        assert last is not None
        raise last

    def _next(self, name: str, state: Mapping[str, Any]) -> tuple[str, ...]:
        if name in self._g._routers:
            routed = self._g._routers[name](dict(state))
            values = (routed,) if isinstance(routed, str) else tuple(routed)
        else:
            values = self._g._edges.get(name, ())
        for value in values:
            self._g._validate_target(value)
        return tuple(values)

    def _merge(self, state: MutableMapping[str, Any], update: Mapping[str, Any]) -> None:
        for key, value in update.items():
            if key in state and key in self._g._reducers:
                state[key] = self._g._reducers[key](state[key], value)
            else:
                state[key] = value


__all__ = [
    "Checkpoint", "CompiledStateGraph", "GraphEvent", "GraphInterrupt",
    "GraphRun", "InMemoryCheckpointStore", "RetryPolicy", "StateGraph",
]
