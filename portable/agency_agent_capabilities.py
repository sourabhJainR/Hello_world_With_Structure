"""Provider-neutral primitives covering the major gaps identified in AI Agent Book v2.

These are small runtime contracts, not provider-specific SDK wrappers. They keep
AER portable while making context, persistent memory, active tools, event-driven
interaction, evolution and multi-agent collaboration executable and testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import time
from typing import Any, Callable, Mapping, Protocol


@dataclass(frozen=True)
class ContextItem:
    key: str
    value: Any
    priority: int = 0
    stable: bool = True
    sensitive: bool = False


@dataclass(frozen=True)
class ContextPack:
    items: tuple[ContextItem, ...]
    token_estimate: int
    omitted: tuple[str, ...] = ()
    digest: str = ""


def build_context(items: list[ContextItem], token_budget: int, reserve_tokens: int = 0) -> ContextPack:
    if token_budget <= 0 or reserve_tokens < 0 or reserve_tokens >= token_budget:
        raise ValueError("invalid context budget")
    available = token_budget - reserve_tokens
    ordered = sorted(items, key=lambda x: (-x.priority, not x.stable, x.key))
    selected: list[ContextItem] = []
    omitted: list[str] = []
    used = 0
    for item in ordered:
        size = max(1, len(str(item.value).split()))
        if used + size <= available:
            selected.append(item)
            used += size
        else:
            omitted.append(item.key)
    payload = [(x.key, str(x.value), x.priority, x.stable) for x in selected]
    digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return ContextPack(tuple(selected), used, tuple(omitted), digest)


@dataclass(frozen=True)
class MemoryFact:
    key: str
    value: str
    kind: str = "semantic"
    source: str = ""
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


class MemoryStore:
    def __init__(self) -> None:
        self._facts: dict[str, MemoryFact] = {}

    def upsert(self, fact: MemoryFact) -> MemoryFact:
        if fact.kind not in {"episodic", "semantic", "procedural"}:
            raise ValueError("unsupported memory kind")
        if not 0 <= fact.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        previous = self._facts.get(fact.key)
        if previous and previous.confidence > fact.confidence and previous.value != fact.value:
            return previous
        self._facts[fact.key] = fact
        return fact

    def get(self, key: str) -> MemoryFact | None:
        return self._facts.get(key)

    def search(self, query: str, limit: int = 8) -> tuple[MemoryFact, ...]:
        terms = {x.lower() for x in query.split() if x}
        scored = []
        for fact in self._facts.values():
            haystack = f"{fact.key} {fact.value} {fact.kind}".lower()
            score = sum(term in haystack for term in terms) + fact.confidence
            if score:
                scored.append((score, fact))
        return tuple(f for _, f in sorted(scored, key=lambda x: (-x[0], x[1].key))[:limit])

    def snapshot(self) -> tuple[MemoryFact, ...]:
        return tuple(sorted(self._facts.values(), key=lambda x: x.key))


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    category: str
    risk: str = "low"
    permissions: tuple[str, ...] = ()
    handler: Callable[..., Any] | None = None


class ToolPolicy(Protocol):
    def allow(self, tool: ToolSpec, arguments: Mapping[str, Any]) -> bool: ...


@dataclass(frozen=True)
class AllowlistedToolPolicy:
    allowed_tools: frozenset[str] = frozenset()
    max_risk: str = "medium"

    def allow(self, tool: ToolSpec, arguments: Mapping[str, Any]) -> bool:
        if self.allowed_tools and tool.name not in self.allowed_tools:
            return False
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order.get(tool.risk, 3) <= order.get(self.max_risk, 1)


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec] | None = None) -> None:
        self._tools = {t.name: t for t in (tools or [])}

    def register(self, tool: ToolSpec) -> None:
        if not tool.name.strip() or tool.handler is None:
            raise ValueError("tool name and handler are required")
        self._tools[tool.name] = tool

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))

    def discover(self, query: str, limit: int = 5) -> tuple[ToolSpec, ...]:
        terms = {x.lower() for x in query.split() if len(x) > 1}
        if not terms:
            return self.list_tools()[:limit]
        ranked = []
        for tool in self._tools.values():
            haystack = f"{tool.name} {tool.description} {tool.category}".lower()
            score = sum(term in haystack for term in terms)
            if score:
                ranked.append((score, tool))
        return tuple(t for _, t in sorted(ranked, key=lambda x: (-x[0], x[1].name))[:limit])

    def execute(self, name: str, arguments: Mapping[str, Any], policy: ToolPolicy) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"unknown tool: {name}")
        if not policy.allow(tool, arguments):
            raise PermissionError(f"tool execution denied: {name}")
        return tool.handler(**dict(arguments))  # type: ignore[misc]


@dataclass(frozen=True)
class AgentEvent:
    event_id: str
    kind: str
    payload: Mapping[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SafePoint:
    name: str
    cancellable: bool = True
    preemptible: bool = True


class EventRuntime:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[AgentEvent], Any]]] = {}
        self._cancelled: set[str] = set()

    def on(self, kind: str, handler: Callable[[AgentEvent], Any]) -> None:
        self._handlers.setdefault(kind, []).append(handler)

    def cancel(self, event_id: str) -> None:
        self._cancelled.add(event_id)

    def dispatch(self, event: AgentEvent) -> list[Any]:
        if event.event_id in self._cancelled:
            return []
        return [handler(event) for handler in self._handlers.get(event.kind, ())]


@dataclass(frozen=True)
class LearningSignal:
    trace_id: str
    outcome: float
    process_rules: tuple[str, ...] = ()
    rubric: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EvolutionCandidate:
    candidate_id: str
    carrier: str
    change: str
    evidence_trace_ids: tuple[str, ...]
    baseline_score: float
    candidate_score: float

    @property
    def improvement(self) -> float:
        return self.candidate_score - self.baseline_score


def validate_candidate(candidate: EvolutionCandidate, minimum_improvement: float = 0.0) -> bool:
    return candidate.improvement >= minimum_improvement and bool(candidate.evidence_trace_ids)


@dataclass(frozen=True)
class AgentNode:
    agent_id: str
    role: str
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class Handoff:
    source: str
    target: str
    task: str
    context_keys: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass
class CollaborationGraph:
    agents: dict[str, AgentNode] = field(default_factory=dict)
    handoffs: list[Handoff] = field(default_factory=list)

    def add_agent(self, agent: AgentNode) -> None:
        self.agents[agent.agent_id] = agent

    def handoff(self, source: str, target: str, task: str, context_keys: tuple[str, ...] = (), evidence_ids: tuple[str, ...] = ()) -> Handoff:
        if source not in self.agents or target not in self.agents:
            raise KeyError("handoff participants must be registered agents")
        item = Handoff(source, target, task, context_keys, evidence_ids)
        self.handoffs.append(item)
        return item

    def topology(self) -> dict[str, Any]:
        return {"agents": [a.__dict__ for a in self.agents.values()], "handoffs": [h.__dict__ for h in self.handoffs]}
