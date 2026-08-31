#!/usr/bin/env python3
"""Dependency-free P2 runtime: model routing, durable memory, risk prediction and eval comparison."""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Callable

VERSION = "1.2"
LEVELS = ("low", "medium", "high", "critical")
REQUIRED_MEMORY_FIELDS = ("id", "version", "topic", "content", "source", "confidence", "created_at", "expires_at", "tags")
_SENSITIVE_CONTENT = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]\s*[^\s,;]{8,}")


def stable_id(prefix: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("stable_id value must be a string")
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def _number(value: Any, *, name: str, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return number


def _complexity(task: dict[str, Any]) -> int:
    value = 0
    for key in ("scope", "blast_radius", "uncertainty", "security_risk", "production_impact"):
        value += max(0, min(3, int(task.get(key, 0))))
    value += 2 if task.get("unknowns") else 0
    value += 2 if task.get("requires_reasoning") else 0
    return value


def route_model(task: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(task, dict):
        raise TypeError("task must be a mapping")
    if not models:
        return {"selected": None, "reason": "no-models", "candidates": []}
    complexity = _complexity(task)
    max_latency = _number(task.get("max_latency_ms", 10**9), name="max_latency_ms", minimum=0)
    max_cost = _number(task.get("max_cost_per_1k", 10**9), name="max_cost_per_1k", minimum=0)
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    rejected: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for model in models:
        name = str(model.get("name", "")).strip()
        if not name or name in seen_names:
            rejected.append({"name": name, "reason": "invalid-or-duplicate-name"})
            continue
        seen_names.add(name)
        capabilities = {str(x) for x in model.get("capabilities", [])}
        if task.get("requires_code") and "code" not in capabilities:
            rejected.append({"name": name, "reason": "missing-code-capability"})
            continue
        if task.get("requires_reasoning") and "reasoning" not in capabilities:
            rejected.append({"name": name, "reason": "missing-reasoning-capability"})
            continue
        latency = _number(model.get("latency_ms", 999999), name=f"{name}.latency_ms", minimum=0)
        cost = _number(model.get("cost_per_1k", 999999), name=f"{name}.cost_per_1k", minimum=0)
        quality = _number(model.get("quality", 0.0), name=f"{name}.quality", minimum=0, maximum=1)
        if latency > max_latency or cost > max_cost:
            rejected.append({"name": name, "reason": "constraint-exceeded"})
            continue
        score = quality * (2.0 if complexity >= 7 else 1.0) + 2.0
        score += 0.5 if complexity < 7 and bool(model.get("fast")) else 0.0
        ranked.append((score, name, model))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return {"selected": None, "reason": "no-compatible-model", "complexity": complexity, "candidates": [], "rejected": rejected}
    return {"selected": ranked[0][2]["name"], "reason": "policy-ranked", "complexity": complexity, "candidates": [m["name"] for _, _, m in ranked], "rejected": rejected}


def memory_record(topic: str, content: str, source: str, confidence: float = 0.5, ttl_seconds: int | None = None, tags: list[str] | None = None, now: int | None = None) -> dict[str, Any]:
    topic, content, source = str(topic).strip(), str(content).strip(), str(source).strip()
    if not topic or not content or not source:
        raise ValueError("topic, content, and source are required")
    if len(content) > 4096:
        raise ValueError("memory content exceeds 4096 characters; store compact observations, not source dumps")
    if _SENSITIVE_CONTENT.search(content):
        raise ValueError("memory content appears to contain a secret-like value")
    confidence_value = _number(confidence, name="confidence", minimum=0, maximum=1)
    if ttl_seconds is not None:
        if isinstance(ttl_seconds, bool) or int(ttl_seconds) < 0:
            raise ValueError("ttl_seconds must be a non-negative integer")
        ttl_seconds = int(ttl_seconds)
    created = int(time.time()) if now is None else int(now)
    expires = created + ttl_seconds if ttl_seconds is not None else None
    return {"id": stable_id("mem", "|".join((topic, content, source))), "version": VERSION, "topic": topic, "content": content, "source": source, "confidence": confidence_value, "created_at": created, "expires_at": expires, "tags": sorted(set(str(x) for x in (tags or [])))}


def validate_memory_record(record: dict[str, Any]) -> list[str]:
    errors = [f"missing:{key}" for key in REQUIRED_MEMORY_FIELDS if key not in record]
    if errors:
        return errors
    if record.get("version") != VERSION:
        errors.append("version")
    if len(str(record.get("content", ""))) > 4096:
        errors.append("content_too_large")
    if _SENSITIVE_CONTENT.search(str(record.get("content", ""))):
        errors.append("sensitive_content")
    try:
        _number(record.get("confidence"), name="confidence", minimum=0, maximum=1)
        created = int(record.get("created_at"))
        expires = record.get("expires_at")
        if expires is not None and int(expires) < created:
            errors.append("invalid_expiry")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def memory_is_active(record: dict[str, Any], now: int | None = None) -> bool:
    if validate_memory_record(record):
        return False
    now = int(time.time()) if now is None else int(now)
    expires = record.get("expires_at")
    return expires is None or int(expires) > now


def select_memory(records: list[dict[str, Any]], topic: str, now: int | None = None, limit: int = 5, predicate: Callable[[dict[str, Any]], bool] | None = None) -> list[dict[str, Any]]:
    if isinstance(limit, bool) or int(limit) < 0 or int(limit) > 100:
        raise ValueError("limit must be an integer from 0 to 100")
    topic = str(topic).strip()
    active = [r for r in records if memory_is_active(r, now) and str(r.get("topic", "")) == topic and (predicate(r) if predicate else True)]
    active.sort(key=lambda r: (-float(r["confidence"]), -int(r["created_at"]), str(r["id"])))
    return active[: int(limit)]


def save_memory(path: Path, records: list[dict[str, Any]]) -> None:
    errors = [f"{idx}:{validate_memory_record(record)}" for idx, record in enumerate(records) if validate_memory_record(record)]
    if errors:
        raise ValueError("invalid memory records: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def predict_change_risk(changed_paths: list[str], fanout: int = 0, coverage: float = 1.0, api_change: bool = False, schema_change: bool = False, historical_defects: int = 0) -> dict[str, Any]:
    paths = [str(p) for p in changed_paths if str(p).strip()]
    fanout = int(_number(fanout, name="fanout", minimum=0))
    historical_defects = int(_number(historical_defects, name="historical_defects", minimum=0))
    coverage = _number(coverage, name="coverage", minimum=0, maximum=1)
    score = min(len(paths), 10) + min(fanout // 5, 6) + (4 if api_change else 0) + (4 if schema_change else 0) + min(historical_defects, 4)
    score += 3 if coverage < 0.5 else 1 if coverage < 0.8 else 0
    level = "low" if score <= 4 else "medium" if score <= 9 else "high" if score <= 14 else "critical"
    controls = {"low": ["focused_verification"], "medium": ["explicit_contract", "regression_verification"], "high": ["impact_analysis", "broader_verification", "independent_review"], "critical": ["explicit_approval", "isolated_execution", "broader_verification", "independent_review"]}[level]
    return {"risk_version": VERSION, "score": score, "level": level, "controls": controls, "drivers": {"changed_files": len(paths), "fanout": fanout, "coverage": coverage, "api_change": bool(api_change), "schema_change": bool(schema_change), "historical_defects": historical_defects}}


def compare_eval_baseline(baseline: dict[str, float], candidate: dict[str, float], required: list[str] | None = None, directions: dict[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise TypeError("baseline and candidate must be mappings")
    required = sorted(set(required or ["accuracy"]))
    directions = directions or {}
    invalid = {k: v for k, v in directions.items() if v not in ("higher", "lower")}
    if invalid:
        raise ValueError("metric directions must be 'higher' or 'lower'")
    missing = sorted(metric for metric in required if metric not in baseline or metric not in candidate)
    regressions: dict[str, Any] = {}
    deltas: dict[str, float] = {}
    for metric in sorted(set(baseline) | set(candidate)):
        if metric not in baseline or metric not in candidate:
            continue
        before = _number(baseline[metric], name=f"baseline.{metric}")
        after = _number(candidate[metric], name=f"candidate.{metric}")
        delta = round(after - before, 6)
        deltas[metric] = delta
        direction = directions.get(metric, "higher")
        worsened = after < before if direction == "higher" else after > before
        if metric in required and worsened:
            regressions[metric] = {"before": before, "after": after, "direction": direction}
    return {"baseline": baseline, "candidate": candidate, "deltas": deltas, "directions": {m: directions.get(m, "higher") for m in sorted(set(baseline) & set(candidate))}, "regressions": regressions, "missing_required": missing, "promotable": not regressions and not missing}
