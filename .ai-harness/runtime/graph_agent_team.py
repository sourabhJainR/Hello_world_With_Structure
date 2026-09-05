#!/usr/bin/env python3
"""Dependency-aware multi-agent team execution with task-scoped shared memory."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


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
    """Append-only memory visible to every agent in one graph run.

    Entries are keyed by the current intent digest, so agents cannot silently
    consume memory from another task. The file is local to the run directory.
    """

    def __init__(self, path: Path, intent_digest: str) -> None:
        self.path = Path(path)
        self.intent_digest = intent_digest
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, *, agent: str, role: str, kind: str, text: str,
                evidence: list[str] | None = None, confidence: float = 0.0) -> str:
        text = str(text).strip()
        payload = {
            "intent_digest": self.intent_digest,
            "agent": agent,
            "role": role,
            "kind": kind,
            "text": text,
            "evidence": sorted(set(evidence or [])),
            "confidence": max(0.0, min(1.0, float(confidence))),
            "created_at": time.time(),
        }
        memory_id = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20]
        payload["id"] = memory_id
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return memory_id

    def snapshot(self, limit: int = 24) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("intent_digest") == self.intent_digest:
                rows.append(row)
        return rows[-max(1, int(limit)):]

    def compact_text(self, limit: int = 6000) -> str:
        rows = self.snapshot()
        if not rows:
            return "No shared task memory yet."
        parts = []
        used = 0
        for row in rows:
            line = f"[{row.get('role')}] {row.get('kind')}: {row.get('text', '')}"
            if used + len(line) + 1 > limit:
                break
            parts.append(line)
            used += len(line) + 1
        return "\n".join(parts)


class GraphAgentTeam:
    """Run a dependency graph of role-specific agents.

    Independent read-only agents run in parallel. Mutating agents are serialized
    and only start after their declared dependencies have completed. Every
    agent receives the latest shared task memory and publishes its output back
    into that memory for downstream agents.
    """

    def __init__(self, agents: list[AgentSpec], *, max_parallel_read_only: int = 4,
                 max_agents: int = 12) -> None:
        self.agents = {agent.name: agent for agent in agents}
        if not self.agents:
            raise ValueError("graph agent team requires at least one agent")
        if len(self.agents) > max_agents:
            raise ValueError("graph agent team exceeds agent budget")
        self.max_parallel_read_only = max(1, int(max_parallel_read_only))
        self._validate()

    def _validate(self) -> None:
        for agent in self.agents.values():
            missing = set(agent.depends_on) - self.agents.keys()
            if missing:
                raise ValueError(f"agent {agent.name} depends on missing agents: {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("agent graph contains a dependency cycle")
            if name in visited:
                return
            visiting.add(name)
            for dependency in self.agents[name].depends_on:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in self.agents:
            visit(name)

    def levels(self) -> list[list[AgentSpec]]:
        remaining = set(self.agents)
        done: set[str] = set()
        result: list[list[AgentSpec]] = []
        while remaining:
            ready = sorted(name for name in remaining if set(self.agents[name].depends_on) <= done)
            if not ready:
                raise ValueError("agent graph could not be scheduled")
            level = [self.agents[name] for name in ready]
            result.append(level)
            done.update(ready)
            remaining.difference_update(ready)
        return result

    def digest(self) -> str:
        payload = [
            {"name": a.name, "role": a.role, "depends_on": list(a.depends_on),
             "read_only": a.read_only, "critical": a.critical, "focus": a.focus}
            for level in self.levels() for a in level
        ]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def execute(
        self,
        *,
        task: str,
        intent_digest: str,
        base_prompt: str,
        memory: SharedTaskMemory,
        invoke_agent: Callable[[AgentSpec, str], tuple[int, str, float]],
    ) -> dict[str, Any]:
        results: dict[str, AgentResult] = {}
        blocked: set[str] = set()

        def run_agent(agent: AgentSpec) -> AgentResult:
            if any(name in blocked or results[name].status != "passed" for name in agent.depends_on):
                return AgentResult(agent.name, agent.role, "blocked", error="dependency failed")
            shared = memory.compact_text()
            prompt = f"""# AER graph agent

You are the {agent.role} agent in a shared-memory engineering team.

Task:
{task}

Intent digest: {intent_digest}
Agent: {agent.name}
Role: {agent.role}
Focus: {agent.focus or 'Use the task contract and repository evidence to perform your role.'}
Read-only: {agent.read_only}

## Shared task memory
{shared}

## Team contract
- Work only on the current task.
- Inspect repository evidence before making claims.
- Do not repeat work already established in shared memory unless verifying it.
- Publish useful findings, decisions, evidence and unresolved risks in your response.
- {'Do not modify files.' if agent.read_only else 'You may modify files only within the task scope.'}
- Downstream agents will receive your output through shared memory.

## Base instructions
{base_prompt}
"""
            code, output, duration = invoke_agent(agent, prompt)
            status = "passed" if code == 0 else "failed"
            result = AgentResult(agent.name, agent.role, status, exit_code=code,
                                 duration_seconds=duration, output=output)
            memory_id = memory.publish(agent=agent.name, role=agent.role, kind="agent_output",
                                       text=output[-12000:], evidence=[f"agent:{agent.name}"],
                                       confidence=0.8 if code == 0 else 0.2)
            result.memory_ids.append(memory_id)
            return result

        for level in self.levels():
            ready = [agent for agent in level if not any(dep in blocked for dep in agent.depends_on)]
            parallel = [agent for agent in ready if agent.read_only]
            serial = [agent for agent in ready if not agent.read_only]
            if parallel:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_parallel_read_only, len(parallel))) as pool:
                    futures = {pool.submit(run_agent, agent): agent for agent in parallel}
                    for future in concurrent.futures.as_completed(futures):
                        agent = futures[future]
                        result = future.result()
                        results[agent.name] = result
                        if result.status != "passed" and agent.critical:
                            blocked.add(agent.name)
            for agent in serial:
                result = run_agent(agent)
                results[agent.name] = result
                if result.status != "passed" and agent.critical:
                    blocked.add(agent.name)

            for agent in ready:
                result = results.get(agent.name)
                if result and result.status != "passed" and agent.critical:
                    blocked.add(agent.name)

        return {
            "graph_digest": self.digest(),
            "intent_digest": intent_digest,
            "agents": {name: result.__dict__ for name, result in results.items()},
            "shared_memory_file": str(memory.path),
            "shared_memory_entries": len(memory.snapshot(500)),
            "accepted": all(result.status == "passed" for result in results.values() if self.agents[result.name].critical),
        }


def team_for_route(route: Mapping[str, Any]) -> GraphAgentTeam:
    """Choose a small role graph from the deterministic route."""
    mode = str(route.get("mode", "implement"))
    caps = set(route.get("capabilities", []))
    agents: list[AgentSpec] = [
        AgentSpec("planner", "planner", read_only=True, focus="Turn the task contract into a small dependency-aware execution plan."),
        AgentSpec("explorer", "explorer", depends_on=("planner",), read_only=True, focus="Trace relevant repository structure, callers, tests and protected behavior."),
    ]
    if mode in {"research", "poc"} or "research" in caps:
        agents.append(AgentSpec("researcher", "researcher", depends_on=("planner",), read_only=True, focus="Gather only task-relevant technical evidence and alternatives."))
    if mode == "debug":
        agents.append(AgentSpec("rca", "RCA investigator", depends_on=("planner", "explorer"), read_only=True, focus="Establish root cause with evidence; do not patch."))
    if mode in {"implement", "debug", "poc"}:
        deps = ["explorer"]
        if "researcher" in {a.name for a in agents}:
            deps.append("researcher")
        if mode == "debug":
            deps.append("rca")
        agents.append(AgentSpec("builder", "builder", depends_on=tuple(deps), read_only=False, focus="Implement the smallest safe task-scoped change."))
        agents.append(AgentSpec("verifier", "verifier", depends_on=("builder",), read_only=True, focus="Run or inspect deterministic verification and identify regressions."))
        review_dep = ("builder", "verifier")
    else:
        review_dep = tuple(a.name for a in agents)
    agents.append(AgentSpec("correctness-reviewer", "correctness reviewer", depends_on=review_dep, read_only=True, focus="Check correctness, compatibility, edge cases and test coverage."))
    if str(route.get("risk", "low")) in {"high", "critical"}:
        agents.append(AgentSpec("security-reviewer", "security reviewer", depends_on=review_dep, read_only=True, focus="Check trust boundaries, permissions, injection, secrets and unsafe defaults."))
        agents.append(AgentSpec("architecture-reviewer", "architecture reviewer", depends_on=review_dep, read_only=True, focus="Check coupling, dependency direction, maintainability and unnecessary complexity."))
    final_deps = tuple(a.name for a in agents if a.name.endswith("reviewer"))
    agents.append(AgentSpec("synthesizer", "team synthesizer", depends_on=final_deps, read_only=True, focus="Synthesize team evidence, unresolved risks and the recommended next action."))
    return GraphAgentTeam(agents)
