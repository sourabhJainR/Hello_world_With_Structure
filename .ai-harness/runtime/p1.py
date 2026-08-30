#!/usr/bin/env python3
"""Dependency-free P1 runtime: repository DNA, regression genome, memory/proof graph and extension negotiation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

VERSION = "1.0"
PROFILE_FIELDS = ("language", "framework", "build", "tests", "error_handling", "logging", "telemetry", "configuration", "dependencies", "api", "data", "deployment", "architecture", "security", "high_risk_areas")


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def profile(repository: str, facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    normalized = {}
    for key in PROFILE_FIELDS:
        item = facts.get(key, {})
        normalized[key] = {"status": item.get("status", "unknown"), "value": item.get("value", ""), "evidence_ids": sorted(set(item.get("evidence_ids", [])))}
    return {"profile_version": VERSION, "repository": repository, "facts": normalized}


def affected_profile_fields(changed_paths: list[str]) -> list[str]:
    result = set()
    for p in changed_paths:
        q = p.lower()
        if q.endswith((".cs", ".java", ".py", ".ts", ".tsx", ".js", ".go", ".rs")): result.update(("language", "framework", "architecture", "error_handling", "logging", "telemetry", "tests"))
        if "test" in q or "spec" in q: result.add("tests")
        if any(x in q for x in ("package", "requirements", "pom.xml", "cargo", "go.mod")): result.add("dependencies")
        if any(x in q for x in ("docker", "helm", "terraform", "deploy", "workflow")): result.add("deployment")
        if any(x in q for x in ("config", "settings", ".env")): result.add("configuration")
        if any(x in q for x in ("api", "controller", "route", "openapi", "swagger")): result.add("api")
        if any(x in q for x in ("migration", "schema", "sql", "model")): result.add("data")
    return sorted(result)


def regression_case(trigger: str, expected: str, constraints: list[str] | None = None) -> dict[str, Any]:
    constraints = constraints or []
    return {"id": stable_id("reg", trigger + "|" + expected), "trigger": trigger, "expected": expected, "constraints": constraints, "deterministic": True}


def regression_result(case: dict[str, Any], observed: str) -> dict[str, Any]:
    return {"case_id": case["id"], "passed": observed == case["expected"], "observed": observed, "expected": case["expected"]}


def graph_node(kind: str, key: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": stable_id(kind, key), "kind": kind, "key": key, "attributes": attributes or {}}


def graph_edge(source: str, relation: str, target: str, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {"source": source, "relation": relation, "target": target, "evidence_ids": sorted(set(evidence_ids or []))}


def extension_manifest(name: str, capabilities: list[str], optional: bool = True) -> dict[str, Any]:
    return {"name": name, "version": VERSION, "optional": optional, "capabilities": sorted(set(capabilities))}


def negotiate(required: list[str], available: list[dict[str, Any]]) -> dict[str, Any]:
    capabilities = {c for item in available for c in item.get("capabilities", [])}
    missing = sorted(set(required) - capabilities)
    return {"compatible": not missing, "required": sorted(set(required)), "available": sorted(capabilities), "missing": missing, "degraded": bool(missing)}


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
