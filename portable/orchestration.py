"""Provider-neutral orchestration primitives for AER.

The engine models the progression from an agent loop to a graph of bounded
agentic and deterministic nodes. It does not call an LLM itself. A provider
adapter supplies node execution; AER owns topology, budgets, evidence,
evaluation, repair policy, and promotion boundaries.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class NodeKind(str, Enum):
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    EVALUATOR = "evaluator"
    HUMAN = "human"
    ROUTER = "router"
    JOIN = "join"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    RUNNING = "running"
    ACCEPTED = "accepted"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Evidence:
    kind: str
    summary: str
    source: str = "runtime"
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.digest:
            payload = f"{self.kind}|{self.source}|{self.summary}".encode()
            object.__setattr__(self, "digest", hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class Node:
    name: str
    kind: NodeKind
    run: Callable[[Mapping[str, Any]], Any]
    depends_on: tuple[str, ...] = ()
    max_attempts: int = 1
    evaluator: Callable[[Any], bool] | None = None
    repair: Callable[[Any, Mapping[str, Any]], Any] | None = None
    critical: bool = True


@dataclass
class NodeResult:
    node: str
    status: NodeStatus
    attempts: int = 0
    output: Any = None
    evidence: list[Evidence] = field(default_factory=list)
    error: str | None = None
    repair_count: int = 0


@dataclass
class OrchestrationRun:
    task_id: str
    intent_digest: str
    status: RunStatus = RunStatus.RUNNING
    results: dict[str, NodeResult] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    learned_candidates: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None
    started_at: float = field(default_factory=time.time)

    def record(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)


class Graph:
    """Small dependency graph with deterministic topological execution order."""

    def __init__(self, nodes: list[Node]) -> None:
        self.nodes = {node.name: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("graph contains duplicate node names")
        self._validate()

    def _validate(self) -> None:
        for node in self.nodes.values():
            missing = set(node.depends_on) - self.nodes.keys()
            if missing:
                raise ValueError(f"node {node.name} depends on missing nodes: {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("graph contains a dependency cycle")
            if name in visited:
                return
            visiting.add(name)
            for dep in self.nodes[name].depends_on:
                visit(dep)
            visiting.remove(name)
            visited.add(name)

        for name in self.nodes:
            visit(name)

    def order(self) -> list[Node]:
        ordered: list[Node] = []
        done: set[str] = set()
        remaining = set(self.nodes)
        while remaining:
            ready = sorted(
                name for name in remaining if set(self.nodes[name].depends_on) <= done
            )
            if not ready:
                raise ValueError("graph could not be ordered")
            for name in ready:
                ordered.append(self.nodes[name])
                done.add(name)
                remaining.remove(name)
        return ordered


class Orchestrator:
    """Execute a graph whose agentic nodes contain bounded local loops."""

    def __init__(
        self,
        graph: Graph,
        *,
        max_total_attempts: int = 32,
        allow_self_improvement: bool = True,
    ) -> None:
        if max_total_attempts < 1:
            raise ValueError("max_total_attempts must be positive")
        self.graph = graph
        self.max_total_attempts = max_total_attempts
        self.allow_self_improvement = allow_self_improvement

    @staticmethod
    def intent_digest(intent: str) -> str:
        return hashlib.sha256(intent.strip().encode()).hexdigest()

    def run(self, task_id: str, intent: str, context: Mapping[str, Any] | None = None) -> OrchestrationRun:
        run = OrchestrationRun(task_id=task_id, intent_digest=self.intent_digest(intent))
        state: dict[str, Any] = dict(context or {})
        state["intent_digest"] = run.intent_digest
        total_attempts = 0

        for node in self.graph.order():
            dependency_results = [run.results[name] for name in node.depends_on]
            if any(result.status in {NodeStatus.FAILED, NodeStatus.BLOCKED} for result in dependency_results):
                result = NodeResult(node.name, NodeStatus.SKIPPED, error="dependency failed")
                run.results[node.name] = result
                if node.critical:
                    run.status = RunStatus.BLOCKED
                    run.stop_reason = f"critical dependency failure before {node.name}"
                    return run
                continue

            result = self._execute_node(node, state, run, total_attempts)
            run.results[node.name] = result
            total_attempts += result.attempts
            if result.evidence:
                run.evidence.extend(result.evidence)
            if result.status in {NodeStatus.FAILED, NodeStatus.BLOCKED} and node.critical:
                run.status = RunStatus.FAILED if result.status == NodeStatus.FAILED else RunStatus.BLOCKED
                run.stop_reason = result.error or f"critical node {node.name} did not pass"
                return run
            state[node.name] = result.output
            if total_attempts >= self.max_total_attempts:
                run.status = RunStatus.BLOCKED
                run.stop_reason = "global attempt budget exhausted"
                return run

        run.status = RunStatus.ACCEPTED
        run.stop_reason = "all critical graph nodes passed"
        if self.allow_self_improvement:
            run.learned_candidates.extend(self._propose_learning(run))
        return run

    def _execute_node(
        self,
        node: Node,
        state: Mapping[str, Any],
        run: OrchestrationRun,
        total_attempts: int,
    ) -> NodeResult:
        attempts = 0
        repairs = 0
        evidence: list[Evidence] = []
        last_output: Any = None
        last_error: str | None = None
        max_attempts = max(1, node.max_attempts)

        while attempts < max_attempts and total_attempts + attempts < self.max_total_attempts:
            attempts += 1
            try:
                output = node.run(state)
                last_output = output
                evidence.append(Evidence("node-output", f"{node.name} attempt {attempts} completed", node.name))
                passed = node.evaluator(output) if node.evaluator else True
                if passed:
                    evidence.append(Evidence("evaluation", f"{node.name} passed on attempt {attempts}", node.name))
                    return NodeResult(node.name, NodeStatus.PASSED, attempts, output, evidence, repair_count=repairs)
                last_error = "evaluator rejected node output"
                evidence.append(Evidence("evaluation-failure", last_error, node.name))
            except Exception as exc:  # provider/tool failures become evidence, not crashes
                last_error = f"{type(exc).__name__}: {exc}"
                evidence.append(Evidence("execution-error", last_error, node.name))

            if node.repair is None or attempts >= max_attempts:
                break
            repairs += 1
            try:
                repaired = node.repair(last_output, state)
                last_output = repaired
                evidence.append(Evidence("repair", f"{node.name} produced a repair candidate {repairs}", node.name))
                # Repair changes state for the next provider invocation without
                # silently becoming a promoted policy.
            except Exception as exc:
                last_error = f"repair {type(exc).__name__}: {exc}"
                evidence.append(Evidence("repair-error", last_error, node.name))
                break

        return NodeResult(node.name, NodeStatus.FAILED, attempts, last_output, evidence, last_error, repairs)

    @staticmethod
    def _propose_learning(run: OrchestrationRun) -> list[dict[str, Any]]:
        repairs = sum(result.repair_count for result in run.results.values())
        failures = sum(1 for result in run.results.values() if result.status == NodeStatus.FAILED)
        if repairs == 0 and failures == 0:
            return []
        return [{
            "type": "strategy-candidate",
            "task_id": run.task_id,
            "intent_digest": run.intent_digest,
            "observations": {
                "repair_count": repairs,
                "failure_count": failures,
                "evidence_count": len(run.evidence),
            },
            "promotion": "proposal-only",
            "requires_regression_evaluation": True,
            "requires_safety_evaluation": True,
        }]

    def replay(self, run: OrchestrationRun) -> dict[str, Any]:
        """Return a stable, evidence-only replay projection.

        Replay never executes provider code. It is intentionally safe for
        regression comparison and can be persisted as a golden run summary.
        """
        return {
            "task_id": run.task_id,
            "intent_digest": run.intent_digest,
            "status": run.status.value,
            "stop_reason": run.stop_reason,
            "nodes": {
                name: {
                    "status": result.status.value,
                    "attempts": result.attempts,
                    "repair_count": result.repair_count,
                    "evidence": [item.digest for item in result.evidence],
                }
                for name, result in run.results.items()
            },
            "evidence": [item.digest for item in run.evidence],
            "learned_candidates": run.learned_candidates,
        }

    def replay_json(self, run: OrchestrationRun) -> str:
        return json.dumps(self.replay(run), sort_keys=True, separators=(",", ":"))
