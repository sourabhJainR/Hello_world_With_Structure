#!/usr/bin/env python3
"""Dependency-free P0 runtime artifacts: state, evidence, proof, risk and friction."""
from __future__ import annotations
import hashlib, json, re, time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
RISK_FIELDS = ("scope", "blast_radius", "reversibility", "data_risk", "security_risk", "production_impact", "contract_risk", "uncertainty")
LEVELS = ("low", "medium", "high", "critical")


def _id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def new_state(task_id: str, goal: str, source: str = "user") -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "task_id": task_id, "status": "intake",
            "intent": {"goal": goal, "source": source, "non_goals": []},
            "contract": {"requirements": [], "acceptance": [], "protected_behavior": [], "assumptions": [], "questions": []},
            "repo_facts": [], "decisions": [], "evidence": [],
            "changeset": {"files": [], "symbols": [], "diff_identity": ""},
            "verification": [], "open_risks": [], "next": []}


def evidence(kind: str, source: str, claim: str, locator: str = "", snapshot: str = "", confidence: str = "medium", freshness: str = "", provenance: str = "") -> dict[str, Any]:
    eid = _id("ev", "|".join((kind, source, locator, snapshot, claim)))
    return {"id": eid, "kind": kind, "source": source, "locator": locator, "snapshot": snapshot,
            "claim": claim, "confidence": confidence, "freshness": freshness, "provenance": provenance}


def add_evidence(state: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if any(x.get("id") == record.get("id") for x in state["evidence"]):
        return state
    state["evidence"].append(record)
    return state


def add_decision(state: dict[str, Any], decision: str, evidence_ids: list[str]) -> dict[str, Any]:
    known = {x["id"] for x in state["evidence"]}
    missing = [x for x in evidence_ids if x not in known]
    if missing:
        raise ValueError(f"decision references missing evidence: {missing}")
    state["decisions"].append({"id": _id("decision", decision + "|" + "|".join(evidence_ids)), "decision": decision, "evidence_ids": evidence_ids})
    return state


def verification(state: dict[str, Any], kind: str, status: str, command: str = "", evidence_ids: list[str] | None = None, details: str = "") -> dict[str, Any]:
    evidence_ids = evidence_ids or []
    known = {x["id"] for x in state["evidence"]}
    missing = [x for x in evidence_ids if x not in known]
    if missing:
        raise ValueError(f"verification references missing evidence: {missing}")
    state["verification"].append({"id": _id("verify", f"{kind}|{command}|{details}"), "kind": kind, "status": status, "command": command, "evidence_ids": evidence_ids, "details": details})
    return state


def risk_level(scores: dict[str, int]) -> str:
    values = [max(0, min(3, int(scores.get(k, 0)))) for k in RISK_FIELDS]
    maximum, total = max(values), sum(values)
    if maximum >= 3 or total >= 15: return "critical"
    if maximum >= 2 or total >= 8: return "high"
    if maximum >= 1 or total >= 3: return "medium"
    return "low"


def risk_controls(level: str) -> list[str]:
    return {"low": ["focused_verification"], "medium": ["explicit_contract", "regression_verification"], "high": ["grill", "impact_analysis", "broader_verification", "independent_review"], "critical": ["explicit_approval", "isolated_execution", "broader_verification", "independent_review"]}[level]


def friction_event(kind: str, signature: str, value: str = "") -> dict[str, Any]:
    return {"timestamp": time.time(), "kind": kind, "signature": signature, "value": value}


def detect_thrash(events: list[dict[str, Any]], window: int = 5) -> dict[str, Any]:
    recent = events[-window:]
    signatures = [str(x.get("signature", "")) for x in recent]
    repeated = len(signatures) >= 3 and len(set(signatures)) == 1
    return {"thrashing": repeated, "sample_size": len(recent), "signature": signatures[-1] if signatures else "", "action": "change_strategy" if repeated else "continue"}


def proof_bundle(state: dict[str, Any]) -> dict[str, Any]:
    payload = {"task_id": state["task_id"], "intent": state.get("intent", {}), "contract": state["contract"], "changeset": state["changeset"],
               "verification": state["verification"], "open_risks": state["open_risks"],
               "evidence_ids": [x["id"] for x in state["evidence"]],
               "decision_ids": [x["id"] for x in state["decisions"]]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"proof_version": "1.0", "proof_id": f"proof-{digest[:16]}", **payload}


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def validate_state(state: dict[str, Any]) -> list[str]:
    required = {"schema_version", "task_id", "status", "intent", "contract", "repo_facts", "decisions", "evidence", "changeset", "verification", "open_risks", "next"}
    errors = [f"missing:{k}" for k in sorted(required - state.keys())]
    if state.get("schema_version") != SCHEMA_VERSION: errors.append("schema_version")
    evidence_ids = {x.get("id") for x in state.get("evidence", [])}
    for d in state.get("decisions", []):
        errors.extend(f"decision:{d.get('id')}:missing-evidence:{x}" for x in d.get("evidence_ids", []) if x not in evidence_ids)
    for v in state.get("verification", []):
        errors.extend(f"verification:{v.get('id')}:missing-evidence:{x}" for x in v.get("evidence_ids", []) if x not in evidence_ids)
    return errors
