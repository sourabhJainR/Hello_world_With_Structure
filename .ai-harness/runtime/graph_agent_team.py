#!/usr/bin/env python3
"""Dependency-aware multi-agent execution with bounded context handoffs."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from portable.agency_state_graph import CheckpointStore, StateGraph
from portable.agent_memory import AgentMemory
from portable.context_engine import ContextEngine, ContextPolicy, handoff_from_output
from portable.learning_steward import LearningSteward
from portable.task_planner import Task, TaskPlan
from runtime.task_memory import guidance


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":
            import msvcrt
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    depends_on: tuple[str, ...] = ()
    read_only: bool = True
    critical: bool = True
    focus: str = ""


@dataclass
class AgentResult:
    name: str
    role: str
    status: str
    attempts: int = 1
    exit_code: int = 0
    duration_seconds: float = 0.0
    output: str = ""
    error: str | None = None
    memory_ids: list[str] = field(default_factory=list)


class SharedTaskMemory:
    """Bounded, run-scoped working memory; durable learning lives elsewhere."""

    def __init__(self, path: Path, intent_digest: str, *, max_entries: int = 256, max_chars: int = 200_000,
                 context_policy: ContextPolicy | None = None) -> None:
        if max_entries < 1 or max_chars < 1:
            raise ValueError("memory budgets must be positive")
        self.path = Path(path)
        self.intent_digest = intent_digest
        self.max_entries, self.max_chars = max_entries, max_chars
        self.context = ContextEngine(context_policy)
        self._lock = threading.RLock()
        self._process_lock = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def project_root(self) -> Path:
        return self.path.parent.parent

    @staticmethod
    def _size(rows: list[dict[str, Any]]) -> int:
        return sum(len(json.dumps(row, ensure_ascii=False, sort_keys=True)) + 1 for row in rows)

    def publish(self, *, agent: str, role: str, kind: str, text: str,
                evidence: list[str] | None = None, confidence: float = 0.0) -> str:
        clean = str(text).strip()
        if not clean: raise ValueError("shared memory text is required")
        payload = {"intent_digest": self.intent_digest, "agent": agent, "role": role, "kind": kind,
                   "text": clean, "evidence": sorted(set(evidence or [])),
                   "confidence": max(0.0, min(1.0, float(confidence))), "created_at": time.time()}
        payload["id"] = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20]
        with self._lock, _file_lock(self._process_lock):
            rows = self.snapshot(self.max_entries)
            rows.append(payload)
            rows = rows[-self.max_entries:]
            while rows and self._size(rows) > self.max_chars:
                rows.pop(0)
            if not rows:
                raise ValueError("shared memory item exceeds the hard memory budget")
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            tmp.replace(self.path)
        return payload["id"]

    def snapshot(self, limit: int = 24) -> list[dict[str, Any]]:
        if limit < 1 or not self.path.exists(): return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try: row = json.loads(line)
                except json.JSONDecodeError: continue
                if isinstance(row, dict) and row.get("intent_digest") == self.intent_digest:
                    rows.append(row)
        return rows[-int(limit):]

    def compact_text(self, *, relevant_agents: set[str] | None = None, limit: int | None = None) -> str:
        rows = self.snapshot(self.max_entries)
        if relevant_agents is not None:
            rows = [row for row in rows if str(row.get("agent", "")) in relevant_agents]
        packed = self.context.pack(self.context.from_memory(rows))
        if limit is not None and limit > 0 and len(packed) > limit:
            return packed[:max(200, limit - 40)] + "\n...[context compacted]"
        return packed


def _private_memory(output: str) -> str:
    in_section = False; lines: list[str] = []
    for raw in str(output).splitlines():
        line = raw.strip()
        if line.lower().startswith("## private memory"): in_section = True; continue
        if in_section and line.startswith("## "): break
        if in_section and line: lines.append(line)
    return "\n".join(lines).strip()


class GraphAgentTeam:
    """Run role agents through one canonical dependency contract and StateGraph."""
    def __init__(self, agents: list[AgentSpec], *, max_parallel_read_only: int = 4,
                 max_agents: int = 12, context_policy: ContextPolicy | None = None) -> None:
        self.agents = {agent.name: agent for agent in agents}
        if not self.agents: raise ValueError("graph agent team requires at least one agent")
        if len(self.agents) > max_agents: raise ValueError("graph agent team exceeds agent budget")
        self.max_parallel_read_only = max(1, int(max_parallel_read_only))
        self.context_policy = context_policy or ContextPolicy()
        self._plan = self._build_task_plan()

    def _build_task_plan(self) -> TaskPlan:
        return TaskPlan([Task(id=a.name, title=a.role, description=a.focus, dependencies=list(a.depends_on),
                              tags=["graph-agent"], acceptance=["agent execution completes successfully"],
                              metadata={"read_only": a.read_only, "critical": a.critical}) for a in self.agents.values()])

    def _validate(self) -> None: self._plan.validate()

    def levels(self) -> list[list[AgentSpec]]:
        plan = self._build_task_plan(); levels: list[list[AgentSpec]] = []
        while True:
            ready = plan.ready(tag="graph-agent")
            if not ready:
                if any(t.status == "pending" for t in plan.tasks.values()): raise ValueError("agent graph could not be scheduled")
                return levels
            levels.append([self.agents[t.id] for t in ready])
            for t in ready: t.status = "done"

    def digest(self) -> str:
        payload = [{"name": a.name, "role": a.role, "depends_on": list(a.depends_on), "read_only": a.read_only,
                     "critical": a.critical, "focus": a.focus} for level in self.levels() for a in level]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _build_execution_graph(self, results: dict[str, AgentResult], *, task: str, intent_digest: str,
                               base_prompt: str, memory: SharedTaskMemory,
                               invoke_agent: Callable[[AgentSpec, str], tuple[int, str, float]]) -> StateGraph:
        graph = StateGraph()
        for agent in self.agents.values():
            def run(state: Mapping[str, Any], agent: AgentSpec = agent) -> Mapping[str, Any]:
                deps = [state.get(f"result:{name}") for name in agent.depends_on]
                if any(not item or item.get("status") != "passed" for item in deps):
                    return {f"result:{agent.name}": {"status": "blocked", "activated": False}}
                relevant = set(agent.depends_on); relevant.add("planner")
                shared_context = memory.compact_text(relevant_agents=relevant)
                historical_learning = guidance(memory.project_root, task, limit=2400)
                private = AgentMemory(memory.project_root, agent.name, run_id=intent_digest).read(limit=2200)
                focus_context = LearningSteward(memory.project_root, run_id=intent_digest, task=task).prompt() if agent.name == "learning-steward" else ""
                prompt = f"""# AER graph agent

You are the {agent.role} agent in a shared-memory engineering team.

## Task contract
{task}

Intent digest: {intent_digest}
Agent: {agent.name}
Role: {agent.role}
Focus: {agent.focus or 'Use the task contract and repository evidence to perform your role.'}
Read-only: {agent.read_only}

## Selected context
{shared_context}

## Reusable lessons from earlier runs
{historical_learning}

## Your private session memory
{private or 'No private memory yet.'}

## Handoff rules
- The execution agent owns execution only. Do not spend task time maintaining team learning or peripheral records.
- You may maintain concise private memory when useful. Put only durable personal working notes in `## PRIVATE MEMORY`.
- Team-wide learnings are not yours to curate; the learning steward owns that job.
- Treat the task contract as authoritative.
- Use only selected, task-relevant context; do not reconstruct the entire prior conversation.
- Verify inherited claims against repository evidence when they matter.
- Do not repeat completed dependency work unless verification requires it.
- Return concise findings, decisions, evidence, unresolved risks and the next action.
- {'Do not modify files.' if agent.read_only else 'You may modify files only within the task scope.'}

{focus_context}

## Base instructions
{base_prompt}
"""
                code, output, duration = invoke_agent(agent, prompt)
                private_note = _private_memory(output)
                if private_note: AgentMemory(memory.project_root, agent.name, run_id=intent_digest).remember(private_note)
                result = AgentResult(agent.name, agent.role, "passed" if code == 0 else "failed", exit_code=code,
                                     duration_seconds=duration, output=output)
                handoff = handoff_from_output(task_id=intent_digest, sender=agent.name, receiver="downstream",
                                              objective=agent.focus or task, output=output, success=code == 0,
                                              max_chars=memory.context.policy.output_chars)
                result.memory_ids.append(memory.publish(agent=agent.name, role=agent.role, kind="handoff",
                                                        text=handoff.render(memory.context.policy.output_chars),
                                                        evidence=[f"agent:{agent.name}"],
                                                        confidence=0.8 if code == 0 else 0.2))
                if agent.name == "learning-steward":
                    LearningSteward(memory.project_root, run_id=intent_digest, task=task).persist(
                        output, evidence_ids=[f"agent:{name}" for name in self.agents if name != agent.name])
                results[agent.name] = result
                payload = result.__dict__.copy(); payload["activated"] = True
                return {f"result:{agent.name}": payload}
            graph.add_node(agent.name, run)
        roots = [a.name for a in self.agents.values() if not a.depends_on]
        for name in roots: graph.add_edge(StateGraph.START, name)
        for agent in self.agents.values():
            for dep in agent.depends_on: graph.add_edge(dep, agent.name)
        return graph
