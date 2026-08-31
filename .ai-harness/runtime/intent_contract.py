#!/usr/bin/env python3
"""Immutable task-intent contract and drift checks."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

VERSION = "1.0"


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(x) for x in value]
    if value is None:
        return None
    return str(value).strip()


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(_normalize(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _terms(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "must", "should", "using", "without"}
    return {w for w in re.findall(r"[a-z0-9_]{4,}", text.lower()) if w not in stop}


def create_intent_contract(task: str, *, source: str = "prompt", non_goals: list[str] | None = None, requirements: list[str] | None = None, constraints: list[str] | None = None, protected_behavior: list[str] | None = None, boundaries: list[str] | None = None, acceptance: list[str] | None = None) -> dict[str, Any]:
    goal = str(task).strip()
    if not goal:
        raise ValueError("task intent cannot be empty")
    contract = {
        "version": VERSION,
        "goal": goal,
        "source": str(source),
        "non_goals": sorted(set(str(x).strip() for x in (non_goals or []) if str(x).strip())),
        "requirements": sorted(set(str(x).strip() for x in (requirements or []) if str(x).strip())),
        "constraints": sorted(set(str(x).strip() for x in (constraints or []) if str(x).strip())),
        "protected_behavior": sorted(set(str(x).strip() for x in (protected_behavior or []) if str(x).strip())),
        "boundaries": sorted(set(str(x).strip() for x in (boundaries or []) if str(x).strip())),
        "acceptance": sorted(set(str(x).strip() for x in (acceptance or []) if str(x).strip())),
    }
    contract["intent_digest"] = _digest(contract)
    return contract


def verify_intent_contract(expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected_digest = str(expected.get("intent_digest", ""))
    observed_copy = dict(observed)
    observed_copy.pop("intent_digest", None)
    observed_digest = _digest(observed_copy) if observed_copy.get("goal") else ""
    reasons: list[str] = []
    if not expected_digest:
        reasons.append("missing_expected_digest")
    if observed_digest and observed_digest != expected_digest:
        reasons.append("intent_digest_mismatch")
    if str(observed.get("goal", "")).strip() != str(expected.get("goal", "")).strip():
        reasons.append("goal_changed")
    if sorted(observed.get("protected_behavior", [])) != sorted(expected.get("protected_behavior", [])):
        reasons.append("protected_behavior_changed")
    if sorted(observed.get("boundaries", [])) != sorted(expected.get("boundaries", [])):
        reasons.append("boundaries_changed")
    return {"version": VERSION, "passed": not reasons, "expected_digest": expected_digest, "observed_digest": observed_digest, "reasons": reasons}


def semantic_alignment(intent: dict[str, Any], text: str) -> dict[str, Any]:
    content = str(text).lower()
    goal_words = _terms(str(intent.get("goal", "")))
    must_words = set().union(*(_terms(str(item)) for item in intent.get("requirements", []) + intent.get("protected_behavior", []))) if goal_words or intent.get("requirements") else set()
    relevant = goal_words | must_words
    overlap = len([x for x in relevant if x in content]) / max(1, len(relevant))
    non_goal_hits = [item for item in intent.get("non_goals", []) if _terms(str(item)) and all(term in content for term in _terms(str(item)))]
    return {"alignment_score": round(overlap, 4), "aligned": overlap >= 0.35, "non_goal_hits": non_goal_hits}
