"""Bounded recursive agency: discover, build, verify, remember, schedule, optimize.

The controller turns the repository's existing graph, memory, verification and
learning pieces into an explicit long-running control cycle. It never grants
new permissions, silently changes scope, or treats self-generated learning as
truth. Every cycle has a budget, evidence, a stop condition and an auditable
receipt.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class WorkItem:
    id: str
    objective: str
    priority: int = 0
    dependencies: tuple[str, ...] = ()
    scope: str = ""


@dataclass(frozen=True)
class CycleObservation:
    cycle: int
    work_item: str
    status: str
    evidence: tuple[str, ...] = ()
    score: float = 0.0
    next_action: str = ""


@dataclass(frozen=True)
class AgencyReceipt:
    objective: str
    result: str
    cycles: tuple[CycleObservation, ...]
    learned: tuple[str, ...] = ()
    scheduled: tuple[str, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        if self.result not in {"complete", "blocked", "budget_exhausted", "approval_required", "no_progress"}:
            raise ValueError("invalid agency result")
        if not self.digest:
            payload = json.dumps({
                "objective": self.objective,
                "result": self.result,
                "cycles": [c.__dict__ for c in self.cycles],
                "learned": list(self.learned),
                "scheduled": list(self.scheduled),
            }, sort_keys=True, separators=(",", ":"))
            object.__setattr__(self, "digest", hashlib.sha256(payload.encode()).hexdigest())


Discover = Callable[[], Sequence[WorkItem]]
Build = Callable[[WorkItem], tuple[bool, Sequence[str]]]
Verify = Callable[[WorkItem], tuple[bool, float, Sequence[str]]]
Remember = Callable[[WorkItem, CycleObservation], Sequence[str]]
Schedule = Callable[[Sequence[WorkItem]], Sequence[str]]
Optimize = Callable[[Sequence[CycleObservation]], Sequence[str]]


class RecursiveAgency:
    """Run bounded autonomous work without allowing autonomy to become authority."""

    def __init__(self, *, max_cycles: int = 8, min_progress_score: float = 0.05) -> None:
        if max_cycles < 1:
            raise ValueError("max_cycles must be positive")
        if not 0.0 <= min_progress_score <= 1.0:
            raise ValueError("min_progress_score must be between 0 and 1")
        self.max_cycles = max_cycles
        self.min_progress_score = min_progress_score

    def run(self, *, objective: str, discover: Discover, build: Build, verify: Verify,
            remember: Remember, schedule: Schedule, optimize: Optimize,
            approval_required: Callable[[WorkItem], bool] | None = None) -> AgencyReceipt:
        if not objective.strip():
            raise ValueError("objective is required")
        cycles: list[CycleObservation] = []
        learned: list[str] = []
        completed: set[str] = set()
        pending = list(discover())
        if not pending:
            return AgencyReceipt(objective, "complete", ())

        for cycle in range(1, self.max_cycles + 1):
            ready = [item for item in pending if item.id not in completed and all(dep in completed for dep in item.dependencies)]
            ready.sort(key=lambda item: (-item.priority, item.id))
            if not ready:
                result = "complete" if all(item.id in completed for item in pending) else "blocked"
                return AgencyReceipt(objective, result, tuple(cycles), tuple(learned), tuple(schedule(pending)))

            item = ready[0]
            if approval_required and approval_required(item):
                cycles.append(CycleObservation(cycle, item.id, "approval_required", next_action="approve the exact work item before execution"))
                return AgencyReceipt(objective, "approval_required", tuple(cycles), tuple(learned), tuple(schedule(pending)))

            started = time.monotonic()
            try:
                built, build_evidence = build(item)
            except Exception as exc:
                cycles.append(CycleObservation(cycle, item.id, "blocked", (f"build_error:{type(exc).__name__}:{exc}",), next_action="inspect build failure"))
                return AgencyReceipt(objective, "blocked", tuple(cycles), tuple(learned), tuple(schedule(pending)))
            if not built:
                cycles.append(CycleObservation(cycle, item.id, "blocked", tuple(build_evidence), next_action="resolve the build blocker"))
                return AgencyReceipt(objective, "blocked", tuple(cycles), tuple(learned), tuple(schedule(pending)))

            try:
                passed, score, verification_evidence = verify(item)
            except Exception as exc:
                cycles.append(CycleObservation(cycle, item.id, "blocked", tuple(build_evidence) + (f"verify_error:{type(exc).__name__}:{exc}",), next_action="inspect verification failure"))
                return AgencyReceipt(objective, "blocked", tuple(cycles), tuple(learned), tuple(schedule(pending)))

            evidence = tuple(dict.fromkeys(tuple(build_evidence) + tuple(verification_evidence)))
            observation = CycleObservation(cycle, item.id, "verified" if passed else "rejected", evidence, max(0.0, min(1.0, float(score))), next_action="continue" if passed else "repair and re-verify")
            cycles.append(observation)
            if not passed:
                lessons = tuple(str(x) for x in remember(item, observation))
                learned.extend(x for x in lessons if x not in learned)
                return AgencyReceipt(objective, "blocked", tuple(cycles), tuple(learned), tuple(schedule(pending)))

            if observation.score < self.min_progress_score:
                return AgencyReceipt(objective, "no_progress", tuple(cycles), tuple(learned), tuple(schedule(pending)))

            completed.add(item.id)
            lessons = tuple(str(x) for x in remember(item, observation))
            learned.extend(x for x in lessons if x not in learned)

            remaining = [x for x in pending if x.id not in completed]
            optimized = tuple(str(x) for x in optimize(tuple(cycles)))
            if optimized:
                learned.extend(x for x in optimized if x not in learned)
            if not remaining:
                return AgencyReceipt(objective, "complete", tuple(cycles), tuple(learned), ())
            if time.monotonic() - started < 0:
                return AgencyReceipt(objective, "blocked", tuple(cycles), tuple(learned), tuple(schedule(remaining)))

        remaining = [x for x in pending if x.id not in completed]
        return AgencyReceipt(objective, "budget_exhausted", tuple(cycles), tuple(learned), tuple(schedule(remaining)))


__all__ = ["AgencyReceipt", "CycleObservation", "RecursiveAgency", "WorkItem"]
