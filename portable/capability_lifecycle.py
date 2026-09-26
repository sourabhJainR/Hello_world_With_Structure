"""Reversible capability graduation with bounded canary and rollback.

Self-improvement is safer when a candidate is not permanently trusted after one
benchmark. This lifecycle records a baseline, runs a bounded canary window, and
promotes only after repeated safe observations. Any material regression or
safety failure rolls the candidate back to the incumbent state.

The lifecycle is decision state only; the orchestrator remains the execution
authority.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

from .persistent_memory import PersistentMemory


@dataclass(frozen=True)
class CapabilityLifecycleReceipt:
    capability_id: str
    state: str
    baseline_score: float
    canary_count: int
    successful_canaries: int
    reasons: tuple[str, ...] = ()


class CapabilityLifecycle:
    """Bounded canary lifecycle for reversible self-improvement."""

    def __init__(
        self,
        memory: PersistentMemory,
        project: str,
        *,
        min_canaries: int = 3,
        regression_tolerance: float = 0.02,
    ) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not project.strip():
            raise ValueError("project is required")
        if min_canaries < 1:
            raise ValueError("min_canaries must be positive")
        if not 0 <= regression_tolerance <= 1:
            raise ValueError("regression_tolerance must be between 0 and 1")
        self.memory = memory
        self.project = project.strip()
        self.min_canaries = min_canaries
        self.regression_tolerance = regression_tolerance

    def _rows(self, capability_id: str) -> list[dict]:
        rows = self.memory.search(self.project, capability_id, limit=256)
        result = []
        for row in rows:
            if row.category != "capability-lifecycle":
                continue
            try:
                item = json.loads(row.text)
            except json.JSONDecodeError:
                continue
            if item.get("capability_id") == capability_id:
                result.append(item)
        return result

    def _receipt(self, capability_id: str, baseline: float, rows: list[dict], state: str, reasons=()):
        canaries = [r for r in rows if r.get("event") == "canary"]
        successful = sum(1 for r in canaries if r.get("safe") and float(r.get("score", 0)) + self.regression_tolerance >= baseline)
        return CapabilityLifecycleReceipt(
            capability_id, state, baseline, len(canaries), successful, tuple(reasons)
        )

    def begin(self, capability_id: str, *, baseline_score: float) -> CapabilityLifecycleReceipt:
        if not capability_id.strip():
            raise ValueError("capability_id is required")
        if not 0 <= baseline_score <= 1:
            raise ValueError("baseline_score must be between 0 and 1")
        existing = self._rows(capability_id)
        if any(r.get("event") == "begin" for r in existing):
            raise ValueError("capability lifecycle already exists")
        self.memory.remember(
            self.project,
            "capability-lifecycle",
            json.dumps({
                "event": "begin",
                "capability_id": capability_id.strip(),
                "baseline_score": baseline_score,
            }, sort_keys=True),
            confidence=1.0,
            verified=True,
            approved=True,
        )
        return self._receipt(capability_id.strip(), baseline_score, [], "canary")

    def record_canary(
        self,
        capability_id: str,
        *,
        score: float,
        evidence_id: str,
        safe: bool = True,
        metadata: Mapping[str, object] | None = None,
    ) -> CapabilityLifecycleReceipt:
        if not 0 <= score <= 1:
            raise ValueError("score must be between 0 and 1")
        if not evidence_id.strip():
            raise ValueError("evidence_id is required")
        rows = self._rows(capability_id)
        begins = [r for r in rows if r.get("event") == "begin"]
        if not begins:
            raise KeyError("capability lifecycle has not started")
        baseline = float(begins[-1]["baseline_score"])
        prior = [r for r in rows if r.get("event") == "canary"]
        if any(r.get("evidence_id") == evidence_id for r in prior):
            raise ValueError("evidence_id already recorded")
        regression = score + self.regression_tolerance < baseline
        state = "rolled_back" if (not safe or regression) else "canary"
        reason = "safety gate failed" if not safe else "canary regressed baseline" if regression else ""
        payload = {
            "event": "canary",
            "capability_id": capability_id.strip(),
            "score": score,
            "evidence_id": evidence_id.strip(),
            "safe": bool(safe),
            "metadata": dict(metadata or {}),
        }
        self.memory.remember(
            self.project,
            "capability-lifecycle",
            json.dumps(payload, sort_keys=True, default=str),
            confidence=1.0 if safe else 0.0,
            verified=True,
            approved=True,
        )
        rows = self._rows(capability_id)
        canaries = [r for r in rows if r.get("event") == "canary"]
        if state != "rolled_back" and len(canaries) >= self.min_canaries:
            state = "promoted"
            reason = "bounded canary window passed"
        return self._receipt(capability_id.strip(), baseline, rows, state, (reason,) if reason else ())

    def status(self, capability_id: str) -> CapabilityLifecycleReceipt:
        rows = self._rows(capability_id)
        begins = [r for r in rows if r.get("event") == "begin"]
        if not begins:
            raise KeyError("capability lifecycle has not started")
        baseline = float(begins[-1]["baseline_score"])
        canaries = [r for r in rows if r.get("event") == "canary"]
        if any(not r.get("safe") or float(r.get("score", 0)) + self.regression_tolerance < baseline for r in canaries):
            state = "rolled_back"
        elif len(canaries) >= self.min_canaries:
            state = "promoted"
        else:
            state = "canary"
        return self._receipt(capability_id.strip(), baseline, rows, state)


__all__ = ["CapabilityLifecycle", "CapabilityLifecycleReceipt"]
