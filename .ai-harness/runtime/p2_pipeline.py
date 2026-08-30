#!/usr/bin/env python3
"""P2 orchestration helpers. Advisory only; all material decisions remain evidence/policy driven."""
from __future__ import annotations

from typing import Any

from p0 import add_decision, add_evidence, evidence
from p2 import compare_eval_baseline, memory_record, predict_change_risk, route_model, select_memory


def plan_task(state: dict[str, Any], task: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    """Add model-routing and change-risk evidence to an existing P0/P1 state."""
    route = route_model(task, models)
    changed_paths = [str(p) for p in task.get("changed_paths", [])]
    risk = predict_change_risk(
        changed_paths,
        fanout=task.get("fanout", 0),
        coverage=task.get("coverage", 1.0),
        api_change=bool(task.get("api_change", False)),
        schema_change=bool(task.get("schema_change", False)),
        historical_defects=task.get("historical_defects", 0),
    )
    route_ev = evidence("tool", "p2.model-routing", "Model routing decision", snapshot=str(route), confidence="medium", provenance="p2_pipeline.plan_task")
    risk_ev = evidence("tool", "p2.risk", "Change-risk estimate", snapshot=str(risk), confidence="medium", provenance="p2_pipeline.plan_task")
    add_evidence(state, route_ev)
    add_evidence(state, risk_ev)
    add_decision(state, f"model:{route.get('selected') or 'unavailable'}", [route_ev["id"]])
    add_decision(state, f"risk:{risk['level']}", [risk_ev["id"]])
    state.setdefault("metadata", {})["p2"] = {"route": route, "risk": risk}
    return state


def retrieve_memory(state: dict[str, Any], records: list[dict[str, Any]], topic: str, limit: int = 5, now: int | None = None) -> list[dict[str, Any]]:
    """Retrieve bounded advisory memory and attach one evidence record for the selection."""
    selected = select_memory(records, topic, now=now, limit=limit)
    ev = evidence("tool", "p2.memory", f"Selected {len(selected)} memory records for topic", snapshot=topic, confidence="medium", provenance="p2_pipeline.retrieve_memory")
    add_evidence(state, ev)
    state.setdefault("metadata", {})["p2_memory"] = {"topic": topic, "selected_ids": [r["id"] for r in selected], "evidence_id": ev["id"]}
    return selected


def promote_eval(baseline: dict[str, float], candidate: dict[str, float], required: list[str] | None = None) -> dict[str, Any]:
    """Return an explicit promotion decision; missing required metrics always block promotion."""
    return compare_eval_baseline(baseline, candidate, required=required)


def seed_memory(topic: str, content: str, source: str, confidence: float = 0.5, ttl_seconds: int | None = None, tags: list[str] | None = None, now: int | None = None) -> dict[str, Any]:
    return memory_record(topic, content, source, confidence, ttl_seconds, tags, now)
