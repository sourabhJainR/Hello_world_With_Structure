#!/usr/bin/env python3
"""Deterministic context planning for AI coding turns.

The planner turns task/risk/phase signals into a bounded retrieval plan. It does
not retrieve files itself; providers supply evidence candidates and this layer
ranks the evidence before prompt construction. Learned policy hints can tune
retrieval without bypassing explicit risk, security, or repository rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    evidence_id: str
    kind: str
    text: str
    relevance: float = 0.0
    confidence: float = 0.0
    freshness: float = 0.0
    cost: int = 1
    source: str = "unknown"

    def score(self) -> float:
        """Rank evidence while penalizing expensive context."""
        quality = (
            0.55 * max(0.0, min(1.0, self.relevance))
            + 0.20 * max(0.0, min(1.0, self.confidence))
            + 0.15 * max(0.0, min(1.0, self.freshness))
        )
        cost_penalty = min(0.10, max(0, self.cost) / 10000.0)
        return quality - cost_penalty


@dataclass(frozen=True, slots=True)
class ContextPlan:
    phase: str
    retrieval_modes: tuple[str, ...]
    budget: int
    max_items: int
    require_fresh_verification: bool
    policy_strategy: str | None = None


def plan_context(*, phase: str, risk: str = "medium", uncertainty: str = "medium",
                 policy_strategy: str | None = None) -> ContextPlan:
    """Select retrieval modes and a bounded budget for one agent phase."""
    phase = phase.lower().strip()
    risk = risk.lower().strip()
    uncertainty = uncertainty.lower().strip()

    modes: list[str] = ["instructions", "task_contract", "lexical"]
    if uncertainty in {"high", "unknown"} or phase in {"research", "investigate"}:
        modes += ["semantic", "history"]
    if phase in {"debug", "implement", "review", "verify"}:
        modes.append("structural")
    if phase in {"implement", "review", "verify"}:
        modes.append("memory")
    if risk in {"high", "critical"}:
        modes += ["security", "history"]

    strategy = (policy_strategy or "").strip().lower()
    if strategy in {"targeted_context", "structural_first"}:
        modes = ["instructions", "task_contract", "structural", "lexical", *(["memory"] if phase in {"implement", "review", "verify"} else [])]
    elif strategy in {"semantic_first", "research_first"} and "semantic" not in modes:
        modes.insert(3, "semantic")
    elif strategy in {"history_first", "regression_history"} and "history" not in modes:
        modes.append("history")

    modes = list(dict.fromkeys(modes))
    budgets = {"low": 9000, "medium": 14000, "high": 20000, "critical": 24000}
    return ContextPlan(
        phase=phase,
        retrieval_modes=tuple(modes),
        budget=budgets.get(risk, budgets["medium"]),
        max_items=24 if risk in {"high", "critical"} else 18,
        require_fresh_verification=risk in {"high", "critical"} or phase == "verify",
        policy_strategy=policy_strategy,
    )


def select_evidence(candidates: Iterable[EvidenceCandidate], *, budget: int, max_items: int) -> list[EvidenceCandidate]:
    """Rank, deduplicate by evidence id and fit candidates into a hard budget."""
    ranked = sorted(candidates, key=lambda item: (item.score(), item.evidence_id), reverse=True)
    selected: list[EvidenceCandidate] = []
    seen: set[str] = set()
    used = 0
    for item in ranked:
        if item.evidence_id in seen:
            continue
        if item.cost < 0 or item.cost > budget - used:
            continue
        selected.append(item)
        seen.add(item.evidence_id)
        used += item.cost
        if len(selected) >= max(1, int(max_items)):
            break
    return selected
