#!/usr/bin/env python3
"""Provider-neutral learning engine for AER.

The engine turns verified outcomes into bounded policy candidates. It never
writes executable policy itself; callers must evaluate candidates against a
regression corpus and safety gate before promotion.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Iterable
import json


@dataclass(frozen=True, slots=True)
class Observation:
    task_id: str
    task_class: str
    strategy: str
    success: bool
    accepted: bool
    verification_passed: bool
    retries: int = 0
    regressions: int = 0
    cost: float = 0.0
    latency_ms: int = 0


@dataclass(frozen=True, slots=True)
class PolicyCandidate:
    policy_id: str
    task_class: str
    strategy: str
    reason: str
    evidence: tuple[str, ...]
    confidence: float
    risk: str = "medium"


def _id(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "policy-" + sha256(raw.encode()).hexdigest()[:16]


def learn(observations: Iterable[Observation], min_samples: int = 3) -> list[PolicyCandidate]:
    """Recommend strategies with repeated verified success and low rework."""
    groups: dict[tuple[str, str], list[Observation]] = {}
    for row in observations:
        groups.setdefault((row.task_class, row.strategy), []).append(row)

    candidates: list[PolicyCandidate] = []
    for (task_class, strategy), rows in groups.items():
        if len(rows) < min_samples:
            continue
        quality = sum(r.success and r.accepted and r.verification_passed and r.regressions == 0 for r in rows) / len(rows)
        if quality < 0.80:
            continue
        avg_retry = sum(r.retries for r in rows) / len(rows)
        confidence = min(0.97, 0.55 + 0.10 * len(rows) + 0.20 * quality - 0.03 * avg_retry)
        evidence = tuple(r.task_id for r in rows)
        candidates.append(PolicyCandidate(
            policy_id=_id({"task_class": task_class, "strategy": strategy, "evidence": evidence}),
            task_class=task_class,
            strategy=strategy,
            reason=f"{len(rows)} observations show {quality:.0%} verified accepted outcomes with {avg_retry:.1f} average retries.",
            evidence=evidence,
            confidence=confidence,
            risk="low" if quality >= 0.90 else "medium",
        ))
    return sorted(candidates, key=lambda x: (x.confidence, x.policy_id), reverse=True)


def candidate_record(candidate: PolicyCandidate) -> dict[str, object]:
    return {"type": "policy_candidate", **asdict(candidate)}
