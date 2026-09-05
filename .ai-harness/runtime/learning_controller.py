#!/usr/bin/env python3
"""Closed-loop learning controller: observe -> score -> replay -> shadow -> canary -> promote -> rollback."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import time
try:
    from .canary_evaluator import CanaryPlan, EvaluationReport, evaluate_shadow, evaluate_staged_canary
    from .context_planner import ContextPlan, plan_context
    from .experience_store import Experience, ExperienceStore
    from .learning_engine import Observation, PolicyCandidate, learn, score_candidates
    from .policy_registry import Policy, PolicyRegistry
    from .regression_memory import RegressionKnowledge, RegressionMemory
    from .regression_replay import ReplayCase, ReplayResult, replay
    from .regression_selector import SelectedRegressionSet, select_regressions, selection_fingerprint
    from .rollback_controller import PolicyHealth, should_rollback
except ImportError:
    from canary_evaluator import CanaryPlan, EvaluationReport, evaluate_shadow, evaluate_staged_canary
    from context_planner import ContextPlan, plan_context
    from experience_store import Experience, ExperienceStore
    from learning_engine import Observation, PolicyCandidate, learn, score_candidates
    from policy_registry import Policy, PolicyRegistry
    from regression_memory import RegressionKnowledge, RegressionMemory
    from regression_replay import ReplayCase, ReplayResult, replay
    from regression_selector import SelectedRegressionSet, select_regressions, selection_fingerprint
    from rollback_controller import PolicyHealth, should_rollback

class LearningController:
    """Own learning state while never granting execution authority."""
    def __init__(self, root: Path, *, registry: PolicyRegistry | None = None) -> None:
        self.root = Path(root); self.learn_dir = self.root / ".ai-harness" / "learning"; self.registry_path = self.learn_dir / "policy-registry.jsonl"
        self.experience_store = ExperienceStore(self.learn_dir / "experience.db")
        self.regression_memory = RegressionMemory(self.learn_dir / "regression-memory.db")
        if registry is not None: self.registry = registry
        elif self.registry_path.exists(): self.registry = PolicyRegistry.from_jsonl(self.registry_path.read_text(encoding="utf-8"))
        else: self.registry = PolicyRegistry()
        self.audit_path = self.learn_dir / "policy-events.jsonl"

    def observe(self, *, task_id: str, task_class: str, strategy: str, success: bool, accepted: bool, verification_passed: bool, retries: int = 0, regressions: int = 0, cost: float = 0.0, latency_ms: float = 0.0, safety_passed: bool = True, evidence_score: float = 1.0, environment_fingerprint: str = "", policy_id: str = "", transfer_key: str = "", failure_class: str = "", metadata: dict[str, Any] | None = None) -> Observation:
        observation = Observation(task_id=str(task_id), task_class=str(task_class), strategy=str(strategy), success=bool(success), accepted=bool(accepted), verification_passed=bool(verification_passed), retries=max(0, int(retries)), regressions=max(0, int(regressions)), cost=max(0.0, float(cost)), latency_ms=max(0.0, float(latency_ms)), safety_passed=bool(safety_passed), evidence_score=max(0.0, min(1.0, float(evidence_score))), environment_fingerprint=str(environment_fingerprint), policy_id=str(policy_id), transfer_key=str(transfer_key or task_class), failure_class=str(failure_class), timestamp=int(time.time()))
        self.experience_store.record(Experience(**asdict(observation), metadata=dict(metadata or {}))); self._append("observation", asdict(observation)); return observation

    def record_regression(self, *, task_family: str, component: str = "", subsystem: str = "", failure_signature: str = "", invariant: str = "", symptom: str = "", reproduction: str = "", fix: str = "", test_pointer: str = "", evidence_pointer: str = "", severity: str = "medium", confidence: float = 0.0, source_kind: str = "observation", source_ref: str = "", verified: bool = False) -> str:
        item = RegressionKnowledge(RegressionMemory.fingerprint(task_family=task_family, component=component, failure_signature=failure_signature, invariant=invariant), task_family, component, subsystem, failure_signature, invariant, symptom, reproduction, fix, test_pointer, evidence_pointer, severity, confidence, source_kind, source_ref)
        knowledge_id = self.regression_memory.record(item, verified=verified); self._append("regression-knowledge", {"knowledge_id": knowledge_id, "verified": verified, "task_family": task_family, "source_ref": source_ref}); return knowledge_id

    def observe_turn(self, snapshot: dict[str, Any], *, task_class: str, strategy: str) -> Observation:
        decision = snapshot.get("decision", {}) if isinstance(snapshot.get("decision"), dict) else {}; verification = float(snapshot.get("verification_score", 0.0) or 0.0); observations = snapshot.get("observations", []) if isinstance(snapshot.get("observations"), list) else []
        failures = sum(1 for row in observations if isinstance(row, dict) and (row.get("status") in {"failed", "error"} or row.get("error"))); state = str(snapshot.get("state", ""))
        return self.observe(task_id=str(snapshot.get("turn_id", "unknown")), task_class=task_class, strategy=strategy, success=state == "completed", accepted=state == "completed" and decision.get("action") != "repair", verification_passed=verification >= 0.75, retries=failures, regressions=int(snapshot.get("regressions", 0) or 0), cost=float((snapshot.get("usage") or {}).get("total_tokens", 0) or 0), latency_ms=float(snapshot.get("latency_ms") or (snapshot.get("usage") or {}).get("latency_ms", 0) or 0), safety_passed=bool(snapshot.get("safety_passed", True)), evidence_score=float(snapshot.get("evidence_score", 1.0) or 0), environment_fingerprint=str(snapshot.get("environment_fingerprint", "")), policy_id=str(snapshot.get("policy_id", "")), failure_class=str(snapshot.get("failure_class", "")))

    def experiences(self, task_class: str | None = None, limit: int = 1000) -> list[Observation]:
        rows = self.experience_store.recent(limit) if task_class is None else self.experience_store.by_task_class(task_class, limit); fields = Observation.__dataclass_fields__; return [Observation(**{name: getattr(row, name) for name in fields}) for row in rows]

    def candidate_scores(self, task_class: str, *, min_samples: int = 3, min_lower_bound: float = 0.0, min_improvement: float = 0.03) -> list[Any]:
        incumbent = self.registry.current(task_class); incumbent_score = float(incumbent.score) if incumbent else 0.0; return score_candidates(self.experiences(task_class), task_class=task_class, incumbent=(incumbent.policy_id, incumbent.strategy, incumbent_score) if incumbent else None, min_samples=min_samples, min_lower_bound=min_lower_bound, min_improvement=min_improvement)

    def learn_candidates(self, observations: Iterable[Observation] | None = None, *, min_samples: int = 3, min_lower_bound: float = 0.0, min_improvement: float = 0.03) -> list[PolicyCandidate]:
        rows = list(observations or []); [self.experience_store.record(Experience(**asdict(row), metadata={"source": "controller-input"})) for row in rows]; all_rows = self.experiences(); candidates: list[PolicyCandidate] = []
        for task_class in sorted({r.task_class for r in all_rows}):
            incumbent = self.registry.current(task_class); incumbent_tuple = (incumbent.policy_id, incumbent.strategy, incumbent.score) if incumbent else None; candidates.extend(learn([r for r in all_rows if r.task_class == task_class], min_samples=min_samples, incumbent=incumbent_tuple, min_lower_bound=min_lower_bound, min_improvement=min_improvement))
        for candidate in candidates: self._append("candidate", asdict(candidate))
        return sorted(candidates, key=lambda c: (c.score, c.confidence, c.policy_id), reverse=True)

    def select_regression_cases(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], *, limit: int = 25) -> SelectedRegressionSet:
        case_list = list(cases); rows = self.experiences(candidate.task_class, 1000); historical = [r.task_id for r in rows if r.regressions > 0 or r.failure_class]; recent = [r.task_id for r in rows[:50] if not r.success or r.regressions > 0]; knowledge = self.regression_memory.retrieve(task_family=candidate.task_class, limit=limit)
        selection = select_regressions(case_list, task_class=candidate.task_class, limit=limit, historical_failures=historical, recent_failures=recent, historical_knowledge=knowledge, seed=candidate.evidence_hash); self._append("regression-selection", {"policy_id": candidate.policy_id, "selection": asdict(selection), "fingerprint": selection_fingerprint(selection)}); return selection

    def replay_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], tuple[bool, bool]]) -> ReplayResult:
        result = replay(cases, lambda case: _pair(runner, case, candidate)); self._append("replay", {"policy_id": candidate.policy_id, "passed": result.passed, "cases": result.cases, "failures": list(result.failures)}); return result

    def shadow_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any]) -> EvaluationReport:
        report = evaluate_shadow(candidate, cases, runner); self._append("shadow", asdict(report)); return report

    def canary_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any], *, exposures: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 1.0), min_cases_per_stage: int = 3, min_pass_rate: float = 1.0, min_verification_rate: float = 1.0) -> CanaryPlan:
        plan = evaluate_staged_canary(candidate, list(cases), runner, exposures=exposures, min_cases_per_stage=min_cases_per_stage, min_pass_rate=min_pass_rate, min_verification_rate=min_verification_rate); self._append("canary-plan", asdict(plan)); return plan

    def evaluate_and_promote(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], Any], *, min_pass_rate: float = 1.0, min_verification_rate: float = 1.0, exposures: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 1.0), min_cases_per_stage: int = 3, now: int | None = None) -> Policy | None:
        case_list = list(cases); selected = self.select_regression_cases(candidate, case_list); case_map = {c.case_id: c for c in case_list}; selected_cases = [case_map[x] for x in selected.case_ids if x in case_map]
        if not selected_cases: self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "empty-regression-selection"}); return None
        replay_result = self.replay_candidate(candidate, selected_cases, lambda c, p: _pair(runner, c, p))
        if not replay_result.passed: self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "regression-replay"}); return None
        shadow = self.shadow_candidate(candidate, selected_cases, runner)
        if not shadow.gate_passed: self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "shadow-gate", "report": asdict(shadow)}); return None
        canary = self.canary_candidate(candidate, selected_cases, runner, exposures=exposures, min_cases_per_stage=min_cases_per_stage, min_pass_rate=min_pass_rate, min_verification_rate=min_verification_rate)
        if not canary.promoted: self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": canary.reason}); return None
        return self.promote(candidate, replay_result, shadow_report=shadow, canary_plan=canary, now=now)

    def promote(self, candidate: PolicyCandidate, replay_result: ReplayResult, *, canary_report: EvaluationReport | None = None, shadow_report: EvaluationReport | None = None, canary_plan: CanaryPlan | None = None, version: int | None = None, now: int | None = None) -> Policy | None:
        canary_passed = (canary_report is not None and canary_report.gate_passed) or (canary_plan is not None and canary_plan.promoted); shadow_passed = shadow_report is not None and shadow_report.gate_passed
        if not replay_result.passed or not shadow_passed or not canary_passed or candidate.risk not in {"low", "medium"} or candidate.confidence < 0.80: self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "promotion-gate", "replay_passed": replay_result.passed, "shadow_passed": shadow_passed, "canary_passed": canary_passed, "confidence": candidate.confidence, "risk": candidate.risk}); return None
        selected_version = self.registry.next_version(candidate.task_class) if version is None else int(version); current = self.registry.current(candidate.task_class); policy = self.registry.add_candidate(Policy(candidate.policy_id, selected_version, candidate.task_class, candidate.strategy, confidence=float(candidate.confidence), score=float(candidate.score), parent_policy_id=current.policy_id if current else "", evidence_hash=candidate.evidence_hash)); promoted = self.registry.promote(policy.policy_id, policy.version, now=now); self._persist_registry(); self._append("promotion", asdict(promoted)); return promoted

    def monitor(self, health: PolicyHealth, *, now: int | None = None) -> bool:
        rollback = should_rollback(health); self._append("monitor", {**asdict(health), "rollback": rollback, "observed_at": int(time.time()) if now is None else int(now)})
        if rollback:
            active = self.registry.active_for_id(health.policy_id)
            if active is not None: retired = self.registry.rollback(active.policy_id, active.version, now=now, restore_previous=True); self._persist_registry(); self._append("rollback", asdict(retired))
        return rollback

    def active_strategy(self, task_class: str) -> str | None: return self.registry.best_strategy(task_class)
    def context_plan(self, *, task_class: str, phase: str, risk: str = "medium", uncertainty: str = "medium") -> ContextPlan: return plan_context(phase=phase, risk=risk, uncertainty=uncertainty, policy_strategy=self.active_strategy(task_class))
    def _persist_registry(self) -> None:
        self.learn_dir.mkdir(parents=True, exist_ok=True); payload = self.registry.export_jsonl(); tmp = self.registry_path.with_suffix(".tmp"); tmp.write_text(payload + ("\n" if payload else ""), encoding="utf-8"); tmp.replace(self.registry_path)
    def _append(self, event: str, payload: dict[str, Any]) -> None:
        self.learn_dir.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle: handle.write(json.dumps({"timestamp": int(time.time()), "event": event, **payload}, ensure_ascii=False, sort_keys=True) + "\n")

def _pair(runner: Callable[[ReplayCase, PolicyCandidate], Any], case: ReplayCase, candidate: PolicyCandidate) -> tuple[bool, bool]:
    raw = runner(case, candidate)
    if isinstance(raw, dict): return bool(raw.get("success")), bool(raw.get("verified"))
    values = list(raw) if isinstance(raw, tuple) else []
    return (bool(values[0]) if values else False, bool(values[1]) if len(values) > 1 else False)
