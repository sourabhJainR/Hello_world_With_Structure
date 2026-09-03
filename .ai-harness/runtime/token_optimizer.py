#!/usr/bin/env python3
"""Deterministic token-budget controls for provider-neutral coding runs.

The optimizer follows three rules: send only relevant context, use the
smallest model tier that can safely perform the task, and replace repeatable
AI work with deterministic scripts. It never mutates source code or commits
changes.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import re
from typing import Iterable


@dataclass(frozen=True)
class ContextSlice:
    text: str
    score: float
    reason: str


@dataclass(frozen=True)
class RouteDecision:
    tier: str
    reason: str
    estimated_input_tokens: int
    estimated_cost_units: float


@dataclass(frozen=True)
class OptimizationReport:
    original_chars: int
    selected_chars: int
    estimated_input_tokens: int
    compression_ratio: float
    selected_sections: int
    route: RouteDecision
    script_candidate: bool


def estimate_tokens(text: str) -> int:
    return max(0, (len(text) + 3) // 4)


def _terms(text: str) -> set[str]:
    return {x.lower() for x in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}", text)}


def select_relevant_context(query: str, sections: Iterable[str], budget_chars: int) -> list[ContextSlice]:
    """Rank sections by lexical overlap and pack the highest-value evidence.

    The query itself is never returned; only supplied repository evidence is
    selected. This is intentionally deterministic so routing is auditable.
    """
    q = _terms(query)
    ranked: list[ContextSlice] = []
    for section in sections:
        text = str(section).strip()
        if not text:
            continue
        terms = _terms(text)
        overlap = len(q & terms)
        score = overlap / max(1, len(q))
        if overlap == 0 and q:
            # Keep very small structural headers only when no better evidence
            # exists; unrelated large blobs should not consume the budget.
            score = 0.01 if len(text) <= 240 else 0.0
        ranked.append(ContextSlice(text, score, "query-overlap" if overlap else "structural-fallback"))
    ranked.sort(key=lambda x: (-x.score, len(x.text), hashlib.sha256(x.text.encode()).hexdigest()))
    selected: list[ContextSlice] = []
    used = 0
    for item in ranked:
        if item.score <= 0:
            continue
        if used + len(item.text) + 1 > max(0, int(budget_chars)):
            continue
        selected.append(item)
        used += len(item.text) + 1
    return selected


def choose_model_tier(*, task: str, risk: str = "normal", uncertainty: str = "known", verification_failures: int = 0) -> RouteDecision:
    """Apply the Minimum Viable Model rule before escalation."""
    normalized_risk = risk.lower()
    words = _terms(task)
    hard = {"architecture", "migration", "security", "incident", "concurrency", "distributed", "production"}
    simple = {"format", "rename", "summarize", "classification", "documentation", "typo", "changelog"}
    if normalized_risk in {"critical", "high"} or uncertainty == "unknown" or verification_failures >= 2:
        tier, reason = "high", "risk-or-uncertainty-requires-stronger-reasoning"
    elif words & hard:
        tier, reason = "high", "task-signals-complex-reasoning"
    elif words & simple or len(words) <= 4:
        tier, reason = "low", "minimum-viable-model-for-simple-task"
    else:
        tier, reason = "standard", "default-model-for-normal-implementation"
    return RouteDecision(tier, reason, 0, 0.0)


def should_use_script(task: str, repeat_count: int = 0) -> bool:
    """Recommend deterministic automation for repeatable mechanical work."""
    mechanical = ("format", "lint", "generate", "validate", "check", "sync", "convert", "inventory")
    return repeat_count >= 2 or any(word in task.lower() for word in mechanical)


def optimize(query: str, sections: Iterable[str], budget_chars: int, *, risk: str = "normal", uncertainty: str = "known", verification_failures: int = 0, repeat_count: int = 0) -> OptimizationReport:
    original = [str(s) for s in sections if str(s).strip()]
    selected = select_relevant_context(query, original, budget_chars)
    selected_chars = sum(len(x.text) for x in selected)
    route = choose_model_tier(task=query, risk=risk, uncertainty=uncertainty, verification_failures=verification_failures)
    route = RouteDecision(route.tier, route.reason, estimate_tokens("\n".join(x.text for x in selected)), 0.0)
    return OptimizationReport(
        original_chars=sum(len(x) for x in original),
        selected_chars=selected_chars,
        estimated_input_tokens=route.estimated_input_tokens,
        compression_ratio=round(selected_chars / max(1, sum(len(x) for x in original)), 4),
        selected_sections=len(selected),
        route=route,
        script_candidate=should_use_script(query, repeat_count),
    )


def report_dict(report: OptimizationReport) -> dict[str, object]:
    return asdict(report)
