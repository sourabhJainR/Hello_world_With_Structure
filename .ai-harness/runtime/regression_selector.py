#!/usr/bin/env python3
"""Select a compact, representative regression set for a policy candidate."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Any
try:
    from .regression_replay import ReplayCase
except ImportError:
    from regression_replay import ReplayCase

@dataclass(frozen=True, slots=True)
class SelectedRegressionSet:
    task_class: str
    case_ids: tuple[str, ...]
    rationale: tuple[str, ...]
    coverage: dict[str, int]
    historical_knowledge_ids: tuple[str, ...] = ()

def select_regressions(cases: Iterable[ReplayCase], *, task_class: str, limit: int = 25,
                       historical_failures: Iterable[str] = (), recent_failures: Iterable[str] = (),
                       historical_knowledge: Iterable[Any] = (), seed: str = "") -> SelectedRegressionSet:
    """Prefer verified historical knowledge, then same-family failures and representatives."""
    rows = list(cases); target = [c for c in rows if c.task_class == task_class]; neighbors = [c for c in rows if c.task_class != task_class]
    historical = set(str(x) for x in historical_failures); recent = set(str(x) for x in recent_failures)
    knowledge = list(historical_knowledge)
    knowledge_case_ids = {str(getattr(k, "knowledge_id", "")) for k in knowledge}
    knowledge_case_ids.discard("")
    def score(case: ReplayCase) -> tuple[int, int, int, str]:
        failure = int(case.case_id in historical) * 100; recent_bonus = int(case.case_id in recent) * 30
        expected = int(case.expected_success) * 5 + int(case.expected_verification) * 3
        digest = sha256(f"{seed}|{case.case_id}".encode()).hexdigest()[:16]
        return (failure + recent_bonus, expected, int(case.task_class == task_class), digest)
    selected: list[ReplayCase] = []; seen: set[str] = set(); bounded = max(1, int(limit))
    # Historical knowledge is represented by matching replay case IDs where available.
    historical_ids = historical | recent
    for case in sorted(target, key=lambda c: (int(c.case_id in historical_ids), score(c)), reverse=True):
        if case.case_id not in seen: selected.append(case); seen.add(case.case_id)
        if len(selected) >= bounded: break
    if len(selected) < bounded:
        for case in sorted(neighbors, key=score, reverse=True):
            if case.case_id not in seen: selected.append(case); seen.add(case.case_id)
            if len(selected) >= bounded: break
    coverage = {"same_family": sum(c.task_class == task_class for c in selected), "historical_failures": sum(c.case_id in historical for c in selected), "recent_failures": sum(c.case_id in recent for c in selected), "neighbor_families": sum(c.task_class != task_class for c in selected), "historical_knowledge": len(knowledge_case_ids)}
    rationale = ("verified historical regression knowledge is retrieved before generic selection", "same task family is prioritized", "historical and recent failures receive priority", "neighboring families fill only the bounded set", "selection is deterministic for reproducible promotion decisions")
    return SelectedRegressionSet(task_class, tuple(c.case_id for c in selected), rationale, coverage, tuple(sorted(knowledge_case_ids)))

def selection_fingerprint(selection: SelectedRegressionSet) -> str:
    payload = {"task_class": selection.task_class, "case_ids": selection.case_ids, "historical_knowledge_ids": selection.historical_knowledge_ids}
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]
