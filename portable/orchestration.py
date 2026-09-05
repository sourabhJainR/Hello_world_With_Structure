"""Provider-neutral orchestration primitives for AER.

AER models Agent -> bounded Loop -> Graph -> Orchestration and can learn changes
to its own executable orchestration. Self-modification is candidate-based: a
candidate is compiled and evaluated in isolation, regression and safety gates
must both pass, and only then is the executable overlay atomically promoted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import py_compile
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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


class PromotionStatus(str, Enum):
    CANDIDATE = "candidate"
    REGRESSION_FAILED = "regression_failed"
    SAFETY_FAILED = "safety_failed"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


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


@dataclass(frozen=True)
class OrchestrationCandidate:
    """Executable orchestration proposed by the learning engine.

    ``source`` is treated as untrusted candidate code. It is never imported by
    the active runtime until both gates pass. The candidate module must expose
    ``build_graph()`` returning a :class:`Graph`; this keeps the activation
    contract narrow and makes graph validation part of promotion.
    """

    candidate_id: str
    source: str
    parent_digest: str
    source_digest: str
    created_at: float
    reason: str
    status: PromotionStatus = PromotionStatus.CANDIDATE
    regression: bool | None = None
    safety: bool | None = None

    @classmethod
    def create(cls, source: str, parent_digest: str, reason: str) -> "OrchestrationCandidate":
        source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        candidate_id = hashlib.sha256(f"{parent_digest}:{source_digest}".encode()).hexdigest()[:24]
        return cls(candidate_id, source, parent_digest, source_digest, time.time(), reason)


class SelfModificationEngine:
    """Turn learning output into executable orchestration only through gates.

    The learning engine may silently create and evaluate candidates. Activation
    is automatic once both regression and safety gates pass. Candidates are
    persisted separately from the immutable AER installation, and promotion is
    atomic so a failed write cannot leave a partially active program.
    """

    def __init__(self, active_dir: Path | str | None = None) -> None:
        self.active_dir = Path(active_dir or (Path.home() / ".aer" / "orchestration"))
        self.active_file = self.active_dir / "active.py"
        self.previous_file = self.active_dir / "previous.py"
        self.journal_file = self.active_dir / "promotion.jsonl"

    @staticmethod
    def _validate_candidate(source: str) -> None:
        if not source.strip():
            raise ValueError("self-modification candidate is empty")
        with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as handle:
            handle.write(source)
            path = Path(handle.name)
        try:
            py_compile.compile(str(path), doraise=True)
            spec = importlib.util.spec_from_file_location("aer_candidate_validation", path)
            if spec is None or spec.loader is None:
                raise ValueError("candidate module cannot be loaded")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            build_graph = getattr(module, "build_graph", None)
            if not callable(build_graph):
                raise ValueError("candidate must expose callable build_graph()")
            graph = build_graph()
            if not isinstance(graph, Graph):
                raise ValueError("build_graph() must return Graph")
        finally:
            path.unlink(missing_ok=True)

    def propose(self, source: str, parent_digest: str, reason: str) -> OrchestrationCandidate:
        candidate = OrchestrationCandidate.create(source, parent_digest, reason)
        self._validate_candidate(candidate.source)
        self._append({"event": "candidate", **self._record(candidate)})
        return candidate

    def evaluate_and_promote(
        self,
        candidate: OrchestrationCandidate,
        *,
        regression_gate: Callable[[OrchestrationCandidate], bool],
        safety_gate: Callable[[OrchestrationCandidate], bool],
    ) -> OrchestrationCandidate:
        """Run gates in order and atomically activate a passing candidate."""
        if not callable(regression_gate) or not callable(safety_gate):
            raise ValueError("both regression_gate and safety_gate are required")
        self._validate_candidate(candidate.source)

        regression_ok = bool(regression_gate(candidate))
        if not regression_ok:
            rejected = self._with_status(candidate, PromotionStatus.REGRESSION_FAILED, regression=False)
            self._append({"event": "reject", **self._record(rejected)})
            return rejected

        safety_ok = bool(safety_gate(candidate))
        if not safety_ok:
            rejected = self._with_status(candidate, PromotionStatus.SAFETY_FAILED, regression=True, safety=False)
            self._append({"event": "reject", **self._record(rejected)})
            return rejected

        promoted = self._with_status(candidate, PromotionStatus.PROMOTED, regression=True, safety=True)
        self._activate(promoted)
        self._append({"event": "promote", **self._record(promoted)})
        return promoted

    def rollback(self) -> None:
        if not self.previous_file.is_file():
            raise FileNotFoundError("no previous orchestration version is available")
        self.active_dir.mkdir(parents=True, exist_ok=True)
        temp = self.active_dir / ".active.rollback.tmp"
        temp.write_bytes(self.previous_file.read_bytes())
        os.replace(temp, self.active_file)
        self._append({"event": "rollback", "timestamp": time.time()})

    def _activate(self, candidate: OrchestrationCandidate) -> None:
        self.active_dir.mkdir(parents=True, exist_ok=True)
        if self.active_file.is_file():
            os.replace(self.active_file, self.previous_file)
        temp = self.active_dir / ".active.tmp"
        temp.write_text(candidate.source, encoding="utf-8")
        self._validate_candidate(temp.read_text(encoding="utf-8"))
        os.replace(temp, self.active_file)

    def _append(self, value: dict[str, Any]) -> None:
        self.active_dir.mkdir(parents=True, exist_ok=True)
        with self.journal_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, sort_keys=True) + "\n")

    @staticmethod
    def _record(candidate: OrchestrationCandidate) -> dict[str, Any]:
        return {
            "candidate_id": candidate.candidate_id,
            "parent_digest": candidate.parent_digest,
            "source_digest": candidate.source_digest,
            "created_at": candidate.created_at,
            "reason": candidate.reason,
            "status": candidate.status.value,
            "regression": candidate.regression,
            "safety": candidate.safety,
        }

    @staticmethod
    def _with_status(candidate: OrchestrationCandidate, status: PromotionStatus, *, regression: bool | None = None, safety: bool | None = None) -> OrchestrationCandidate:
        return OrchestrationCandidate(
            candidate.candidate_id,
            candidate.source,
            candidate.parent_digest,
            candidate.source_digest,
            candidate.created_at,
            candidate.reason,
            status,
            regression,
            safety,
        )


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
            ready = sorted(name for name in remaining if set(self.nodes[name].depends_on) <= done)
            if not ready:
                raise ValueError("graph could not be ordered")
            for name in ready:
                ordered.append(self.nodes[name])
                done.add(name)
                remaining.remove(name)
        return ordered


class Orchestrator:
    """Execute a graph whose agentic nodes contain bounded local loops."""

    def __init__(self, graph: Graph, *, max_total_attempts: int = 32, allow_self_improvement: bool = True) -> None:
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

    def _execute_node(self, node: Node, state: Mapping[str, Any], run: OrchestrationRun, total_attempts: int) -> NodeResult:
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
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                evidence.append(Evidence("execution-error", last_error, node.name))

            if node.repair is None or attempts >= max_attempts:
                break
            repairs += 1
            try:
                last_output = node.repair(last_output, state)
                evidence.append(Evidence("repair", f"{node.name} produced a repair candidate {repairs}", node.name))
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
            "observations": {"repair_count": repairs, "failure_count": failures, "evidence_count": len(run.evidence)},
            "promotion": "candidate -> regression -> safety -> active",
            "requires_regression_evaluation": True,
            "requires_safety_evaluation": True,
        }]

    def replay(self, run: OrchestrationRun) -> dict[str, Any]:
        return {
            "task_id": run.task_id,
            "intent_digest": run.intent_digest,
            "status": run.status.value,
            "stop_reason": run.stop_reason,
            "nodes": {name: {"status": result.status.value, "attempts": result.attempts, "repair_count": result.repair_count, "evidence": [item.digest for item in result.evidence]} for name, result in run.results.items()},
            "evidence": [item.digest for item in run.evidence],
            "learned_candidates": run.learned_candidates,
        }

    def replay_json(self, run: OrchestrationRun) -> str:
        return json.dumps(self.replay(run), sort_keys=True, separators=(",", ":"))
