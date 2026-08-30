#!/usr/bin/env python3
"""Dependency-free P2 runtime: model routing, durable memory, risk prediction and eval comparison."""
from __future__ import annotations

import hashlib
import time
from typing import Any

VERSION = "1.0"


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def _complexity(task: dict[str, Any]) -> int:
    value = 0
    for key in ("scope", "blast_radius", "uncertainty", "security_risk", "production_impact"):
        value += max(0, min(3, int(task.get(key, 0))))
    value += 2 if task.get("unknowns") else 0
    value += 2 if task.get("requires_reasoning") else 0
    return value


def route_model(task: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    if not models:
        return {"selected": None, "reason": "no-models", "candidates": []}
    complexity = _complexity(task)
    ranked = []
    for model in models:
        capabilities = set(model.get("capabilities", []))
        if task.get("requires_code") and "code" not in capabilities:
            continue
        if task.get("requires_reasoning") and "reasoning" not in capabilities:
            continue
        score = 0.0
        score += min(float(model.get("quality", 0.0)), 1.0) * (2.0 if complexity >= 7 else 1.0)
        score += (1.0 if float(model.get("latency_ms", 999999)) <= float(task.get("max_latency_ms", 10**9)) else -2.0)
        score += (1.0 if float(model.get("cost_per_1k", 999999)) <= float(task.get("max_cost_per_1k", 10**9)) else -2.0)
        score += 0.5 if complexity < 7 and model.get("fast") else 0.0
        ranked.append((score, str(model.get("name", "")), model))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return {"selected": None, "reason": "no-compatible-model", "candidates": []}
    return {"selected": ranked[0][2]["name"], "reason": "policy-ranked", "complexity": complexity, "candidates": [m["name"] for _, _, m in ranked]}


def memory_record(topic: str, content: str, source: str, confidence: float = 0.5, ttl_seconds: int | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    created = int(time.time())
    expires = created + ttl_seconds if ttl_seconds is not None else None
    return {"id": stable_id("mem", "|".join((topic, content, source))), "version": VERSION, "topic": topic, "content": content, "source": source, "confidence": max(0.0, min(1.0, confidence)), "created_at": created, "expires_at": expires, "tags": sorted(set(tags or []))}


def memory_is_active(record: dict[str, Any], now: int | None = None) -> bool:
    now = int(time.time()) if now is None else now
    return record.get("expires_at") is None or int(record["expires_at"]) > now


def select_memory(records: list[dict[str, Any]], topic: str, now: int | None = None, limit: int = 5) -> list[dict[str, Any]]:
    active = [r for r in records if memory_is_active(r, now) and str(r.get("topic", "")) == topic]
    active.sort(key=lambda r: (-float(r.get("confidence", 0.0)), -int(r.get("created_at", 0)), str(r.get("id", ""))))
    return active[: max(0, limit)]


def predict_change_risk(changed_paths: list[str], fanout: int = 0, coverage: float = 1.0, api_change: bool = False, schema_change: bool = False, historical_defects: int = 0) -> dict[str, Any]:
    paths = [str(p) for p in changed_paths]
    score = min(len(paths), 10) + min(max(fanout, 0) // 5, 6) + (4 if api_change else 0) + (4 if schema_change else 0) + min(max(historical_defects, 0), 4)
    score += 3 if coverage < 0.5 else 1 if coverage < 0.8 else 0
    level = "low" if score <= 4 else "medium" if score <= 9 else "high" if score <= 14 else "critical"
    controls = {"low": ["focused_verification"], "medium": ["regression_verification"], "high": ["impact_analysis", "broader_verification", "independent_review"], "critical": ["explicit_approval", "isolated_execution", "broader_verification", "independent_review"]}[level]
    return {"risk_version": VERSION, "score": score, "level": level, "controls": controls, "drivers": {"changed_files": len(paths), "fanout": max(fanout, 0), "coverage": max(0.0, min(1.0, coverage)), "api_change": api_change, "schema_change": schema_change, "historical_defects": max(historical_defects, 0)}}


def compare_eval_baseline(baseline: dict[str, float], candidate: dict[str, float], required: list[str] | None = None) -> dict[str, Any]:
    required = required or ["accuracy"]
    regressions = {}
    deltas = {}
    for metric in sorted(set(baseline) | set(candidate)):
        before, after = float(baseline.get(metric, 0.0)), float(candidate.get(metric, 0.0))
        deltas[metric] = round(after - before, 6)
        if metric in required and after < before:
            regressions[metric] = {"before": before, "after": after}
    return {"baseline": baseline, "candidate": candidate, "deltas": deltas, "regressions": regressions, "promotable": not regressions}
