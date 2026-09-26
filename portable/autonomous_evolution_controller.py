"""Failure-triggered autonomous evolution controller.

Turns repeated unresolved outcomes into bounded invention requests. The
controller never changes execution authority; it only opens a gated invention
opportunity once repeated evidence crosses the configured threshold.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .autonomous_capability_invention import (
    AutonomousCapabilityInvention,
    CapabilityComposition,
    HoldoutResult,
    InventionReceipt,
    SafetyResult,
)
from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class EvolutionTrigger:
    triggered: bool
    problem: str
    failure_count: int
    trigger_evidence: tuple[str, ...]
    reason: str


class AutonomousEvolutionController:
    def __init__(self, memory: PersistentMemory, project: str, *, threshold: int = 3) -> None:
        if threshold < 2:
            raise ValueError("evolution threshold must be at least 2")
        self.memory = memory
        self.project = project
        self.threshold = threshold

    @staticmethod
    def _key(problem: str) -> str:
        return hashlib.sha256(problem.strip().encode()).hexdigest()[:24]

    def observe_failure(
        self,
        problem: str,
        *,
        evidence_id: str,
        unresolved: bool = True,
        metadata: Mapping[str, object] | None = None,
    ) -> EvolutionTrigger:
        if not problem.strip():
            raise ValueError("problem is required")
        if not evidence_id.strip():
            raise ValueError("evidence_id is required")
        if not unresolved:
            return EvolutionTrigger(False, problem, 0, (), "outcome resolved")
        key = self._key(problem)
        payload = {
            "problem": problem.strip(),
            "key": key,
            "evidence_id": evidence_id.strip(),
            "metadata": dict(metadata or {}),
        }
        record = self.memory.remember(
            self.project,
            "autonomous-evolution-failure",
            json.dumps(payload, sort_keys=True, default=str),
            confidence=0.8,
            verified=True,
            approved=True,
        )
        # Memory may deduplicate an identical event; search is the canonical count.
        rows = self.memory.search(self.project, key, limit=128)
        events = []
        for row in rows:
            if row.category != "autonomous-evolution-failure":
                continue
            try:
                item = json.loads(row.text)
            except json.JSONDecodeError:
                continue
            if item.get("key") == key:
                events.append(item)
        evidence = tuple(dict.fromkeys(str(item.get("evidence_id", "")) for item in events if item.get("evidence_id")))
        triggered = len(evidence) >= self.threshold
        return EvolutionTrigger(
            triggered,
            problem.strip(),
            len(evidence),
            evidence,
            "repeated unresolved outcomes crossed the invention threshold" if triggered else "failure recorded below invention threshold",
        )

    def invent_if_triggered(
        self,
        trigger: EvolutionTrigger,
        *,
        incumbent: CapabilityComposition,
        available_capabilities: Sequence[str],
        holdout_ids: Sequence[str],
        evaluate,
        safety_gate,
        strategy: str = "default",
    ) -> InventionReceipt | None:
        if not trigger.triggered:
            return None
        engine = AutonomousCapabilityInvention(self.memory, self.project)
        return engine.invent(
            trigger.problem,
            incumbent=incumbent,
            available_capabilities=available_capabilities,
            holdout_ids=holdout_ids,
            evaluate=evaluate,
            safety_gate=safety_gate,
            trigger_evidence=trigger.trigger_evidence,
            strategy=strategy,
        )


__all__ = ["AutonomousEvolutionController", "EvolutionTrigger"]
