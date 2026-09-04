#!/usr/bin/env python3
"""Closed-loop learning controller: observe -> learn -> shadow -> canary -> promote -> monitor -> rollback."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import time

# Support both package imports (runtime.learning_controller) and the legacy
# harness path where .ai-harness/runtime is placed directly on sys.path.
try:
    from .canary_evaluator import EvaluationReport, evaluate_canary, evaluate_shadow
    from .context_planner import ContextPlan, plan_context
    from .learning_engine import Observation, PolicyCandidate, learn
    from .policy_registry import Policy, PolicyRegistry
    from .regression_replay import ReplayCase, ReplayResult, replay
    from .rollback_controller import PolicyHealth, should_rollback
except ImportError:
    from canary_evaluator import EvaluationReport, evaluate_canary, evaluate_shadow
    from context_planner import ContextPlan, plan_context
    from learning_engine import Observation, PolicyCandidate, learn
    from policy_registry import Policy, PolicyRegistry
    from regression_replay import ReplayCase, ReplayResult, replay
    from rollback_controller import PolicyHealth, should_rollback


class LearningController:
    """Coordinate learning without ever granting execution authority."""

    def __init__(self, root: Path, *, registry: PolicyRegistry | None = None) -> None:
        self.root = Path(root)
        self.learn_dir = self.root / ".ai-harness" / "learning"
        self.registry_path = self.learn_dir / "policy-registry.jsonl"
        if registry is not None:
            self.registry = registry
        elif self.registry_path.exists():
            self.registry = PolicyRegistry.from_jsonl(self.registry_path.read_text(encoding="utf-8"))
        else:
            self.registry = PolicyRegistry()
        self.audit_path = self.learn_dir / "policy-events.jsonl"

    def observe(self, *, task_id: str, task_class: str, strategy: str, success: bool,
                accepted: bool, verification_passed: bool, retries: int = 0,
                regressions: int = 0, cost: float = 0.0, latency_ms: float = 0.0) -> Observation:
        observation = Observation(
            task_id=str(task_id), task_class=str(task_class), strategy=str(strategy),
            success=bool(success), accepted=bool(accepted),
            verification_passed=bool(verification_passed), retries=int(retries),
            regressions=int(regressions), cost=float(cost), latency_ms=float(latency_ms),
        )
        self._append("observation", asdict(observation))
        return observation

    def observe_turn(self, snapshot: dict[str, Any], *, task_class: str, strategy: str) -> Observation:
        """Convert a completed AgentTurn snapshot into the learning schema."""
        decision = snapshot.get("decision", {}) if isinstance(snapshot.get("decision"), dict) else {}
        verification = float(snapshot.get("verification_score", 0.0) or 0.0)
        observations = snapshot.get("observations", []) if isinstance(snapshot.get("observations"), list) else []
        failures = sum(1 for row in observations if isinstance(row, dict) and (row.get("status") in {"failed", "error"} or row.get("error")))
        state = str(snapshot.get("state", ""))
        return self.observe(
            task_id=str(snapshot.get("turn_id", "unknown")),
            task_class=task_class,
            strategy=str(strategy),
            success=state == "completed",
            accepted=state == "completed" and decision.get("action") != "repair",
            verification_passed=verification >= 0.75,
            retries=max(0, failures),
            regressions=int(snapshot.get("regressions", 0) or 0),
            cost=float((snapshot.get("usage") or {}).get("total_tokens", 0) or 0),
            latency_ms=float((snapshot.get("latency_ms") or (snapshot.get("usage") or {}).get("latency_ms", 0)) or 0),
        )

    def learn_candidates(self, observations: Iterable[Observation], *, min_samples: int = 3) -> list[PolicyCandidate]:
        candidates = learn(list(observations), min_samples=min_samples)
        for candidate in candidates:
            self._append("candidate", asdict(candidate))
        return candidates

    def replay_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], tuple[bool, bool]]) -> ReplayResult:
        result = replay(cases, lambda case: runner(case, candidate))
        self._append("replay", {"policy_id": candidate.policy_id, "passed": result.passed, "cases": result.cases, "failures": list(result.failures)})
        return result

    def shadow_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any]) -> EvaluationReport:
        report = evaluate_shadow(candidate, cases, runner)
        self._append("shadow", asdict(report))
        return report

    def canary_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any], *, min_pass_rate: float = 1.0, min_verification_rate: float = 1.0) -> EvaluationReport:
        report = evaluate_canary(candidate, cases, runner, min_pass_rate=min_pass_rate, min_verification_rate=min_verification_rate)
        self._append("canary", asdict(report))
        return report

    def promote(self, candidate: PolicyCandidate, replay_result: ReplayResult, *, canary_report: EvaluationReport | None = None, version: int | None = None, now: int | None = None) -> Policy | None:
        canary_passed = canary_report is None or canary_report.gate_passed
        if not replay_result.passed or not canary_passed or candidate.risk not in {"low", "medium"} or candidate.confidence < 0.80:
            self._append("promotion.blocked", {
                "policy_id": candidate.policy_id,
                "reason": "safety-gate",
                "replay_passed": replay_result.passed,
                "canary_passed": canary_passed,
                "confidence": candidate.confidence,
                "risk": candidate.risk,
            })
            return None
        selected_version = self.registry.next_version(candidate.task_class) if version is None else int(version)
        policy = self.registry.add_candidate(Policy(
            candidate.policy_id, selected_version, candidate.task_class, candidate.strategy,
            confidence=float(candidate.confidence),
        ))
        promoted = self.registry.promote(policy.policy_id, policy.version, now=now)
        self._persist_registry()
        self._append("promotion", asdict(promoted))
        return promoted

    def monitor(self, health: PolicyHealth, *, now: int | None = None) -> bool:
        rollback = should_rollback(health)
        self._append("monitor", {**asdict(health), "rollback": rollback, "observed_at": int(time.time()) if now is None else now})
        if rollback:
            active = self.registry.active_for_id(health.policy_id)
            if active is not None:
                retired = self.registry.rollback(active.policy_id, active.version, now=now, restore_previous=True)
                self._persist_registry()
                self._append("rollback", asdict(retired))
        return rollback

    def active_strategy(self, task_class: str) -> str | None:
        return self.registry.best_strategy(task_class)

    def context_plan(self, *, task_class: str, phase: str, risk: str = "medium", uncertainty: str = "medium") -> ContextPlan:
        """Make the registry a runtime input while keeping explicit safety inputs authoritative."""
        strategy = self.active_strategy(task_class)
        return plan_context(phase=phase, risk=risk, uncertainty=uncertainty, policy_strategy=strategy)

    def _persist_registry(self) -> None:
        self.learn_dir.mkdir(parents=True, exist_ok=True)
        payload = self.registry.export_jsonl()
        tmp = self.registry_path.with_suffix(".tmp")
        tmp.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
        tmp.replace(self.registry_path)

    def _append(self, event: str, payload: dict[str, Any]) -> None:
        self.learn_dir.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": int(time.time()), "event": event, **payload}
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
