#!/usr/bin/env python3
"""P1 task-pipeline primitives: connect state, repository DNA, risk, extensions and proof."""
from __future__ import annotations

from typing import Any

from p0 import add_decision, add_evidence, evidence, new_state, proof_bundle, risk_controls, risk_level, verification
from p1 import affected_profile_fields, negotiate, profile, regression_case


def build_task_state(task_id: str, goal: str, source: str = "user", facts: dict[str, dict[str, Any]] | None = None, changed_paths: list[str] | None = None) -> dict[str, Any]:
    """Create the smallest useful P0/P1 state for a task before model execution."""
    state = new_state(task_id, goal, source)
    repo_profile = profile("current-repository", facts or {})
    repo_ev = evidence("source", "repository-profile", "Repository DNA snapshot", snapshot=repo_profile.get("profile_version", "1.0"), confidence="high", provenance="p1.profile")
    add_evidence(state, repo_ev)
    state["repo_facts"].append({"evidence_id": repo_ev["id"]})
    state["metadata"] = {"p1_version": "1.0", "profile": repo_profile, "invalidated_profile_fields": affected_profile_fields(changed_paths or [])}
    return state


def apply_route(state: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    """Persist route as an evidence-backed decision and derive verification controls."""
    route_text = str(sorted((str(k), str(v)) for k, v in route.items()))
    ev = evidence("tool", "router", route_text, confidence="high", provenance="p1_pipeline.apply_route")
    add_evidence(state, ev)
    add_decision(state, f"route:{route.get('mode', 'implement')} risk={route.get('risk', 'low')}", [ev["id"]])
    state["status"] = "planned"
    state["metadata"]["route"] = route
    state["metadata"]["risk_controls"] = risk_controls(route.get("risk", "low"))
    return state


def plan_controls(state: dict[str, Any], scores: dict[str, int]) -> dict[str, Any]:
    level = risk_level(scores)
    state["metadata"]["risk"] = {"level": level, "scores": {k: max(0, min(3, int(v))) for k, v in scores.items()}, "controls": risk_controls(level)}
    return state


def negotiate_extensions(state: dict[str, Any], required: list[str], available: list[dict[str, Any]]) -> dict[str, Any]:
    result = negotiate(required, available)
    ev = evidence("tool", "extension-negotiation", str(result), confidence="high", provenance="p1_pipeline.negotiate_extensions")
    add_evidence(state, ev)
    state["metadata"]["extensions"] = result
    return state


def record_verification(state: dict[str, Any], kind: str, status: str, command: str, details: str = "") -> dict[str, Any]:
    ev = evidence("test", command or kind, f"Verification {status}", locator=command, confidence="high", provenance="p1_pipeline.record_verification")
    add_evidence(state, ev)
    verification(state, kind, status, command, [ev["id"]], details)
    return state


def finalize_proof(state: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic proof bundle only; callers still decide whether acceptance criteria are met."""
    return proof_bundle(state)


def seed_regression(trigger: str, expected: str, constraints: list[str] | None = None) -> dict[str, Any]:
    return regression_case(trigger, expected, constraints)
