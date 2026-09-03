#!/usr/bin/env python3
"""Closed-loop learning controller: observe -> learn -> replay -> promote -> monitor -> rollback."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import time

from learning_engine import Observation, PolicyCandidate, learn
from policy_registry import Policy, PolicyRegistry
from regression_replay import ReplayCase, ReplayResult, replay
from rollback_controller import PolicyHealth, should_rollback


class LearningController:
    """Coordinate learning without ever granting execution authority."""

    def __init__(self, root: Path, *, registry: PolicyRegistry | None = None) -> None:
        self.root = Path(root)
        self.learn_dir = self.root / ".ai-harness" / "learning"
        self.registry = registry or PolicyRegistry()
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

    def learn_candidates(self, observations: Iterable[Observation], *, min_samples: int = 3) -> list[PolicyCandidate]:
        candidates = learn(list(observations), min_samples=min_samples)
        for candidate in candidates:
            self._append("candidate", asdict(candidate))
        return candidates

    def replay_candidate(self, candidate: PolicyCandidate, cases: Iterable[ReplayCase], runner: Callable[[ReplayCase, PolicyCandidate], tuple[bool, bool]]) -> ReplayResult:
        result = replay(cases, lambda case: runner(case, candidate))
        self._append("replay", {"policy_id": candidate.policy_id, "passed": result.passed, "cases": result.cases, "failures": list(result.failures)})
        return result

    def promote(self, candidate: PolicyCandidate, replay_result: ReplayResult, *, version: int = 1, now: int | None = None) -> Policy | None:
        if not replay_result.passed or candidate.risk not in {"low", "medium"} or candidate.confidence < 0.80:
            self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "safety-gate", "replay_passed": replay_result.passed, "confidence": candidate.confidence, "risk": candidate.risk})
            return None
        policy = self.registry.add_candidate(Policy(
            candidate.policy_id, int(version), candidate.task_class, candidate.strategy,
            confidence=float(candidate.confidence),
        ))
        active = self.registry.active(candidate.task_class)
        if any(p.version >= policy.version and p.policy_id != policy.policy_id for p in active):
            self._append("promotion.blocked", {"policy_id": candidate.policy_id, "reason": "active-version-conflict"})
            return None
        promoted = self.registry.promote(policy.policy_id, policy.version, now=now)
        self._append("promotion", asdict(promoted))
        return promoted

    def monitor(self, health: PolicyHealth, *, now: int | None = None) -> bool:
        rollback = should_rollback(health)
        self._append("monitor", {**asdict(health), "rollback": rollback, "observed_at": int(time.time()) if now is None else now})
        if rollback:
            active = self.registry.active_for_id(health.policy_id)
            if active is not None:
                retired = self.registry.rollback(active.policy_id, active.version, now=now, restore_previous=True)
                self._append("rollback", asdict(retired))
        return rollback

    def active_strategy(self, task_class: str) -> str | None:
        return self.registry.best_strategy(task_class)

    def _append(self, event: str, payload: dict[str, Any]) -> None:
        self.learn_dir.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": int(time.time()), "event": event, **payload}
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
