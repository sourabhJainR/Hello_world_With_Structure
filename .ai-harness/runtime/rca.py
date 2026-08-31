#!/usr/bin/env python3
"""Evidence-first RCA helpers. RCA is analysis-only: it never creates or applies patches."""
from __future__ import annotations
import hashlib
import json
from typing import Any

VERSION = "1.0"


def _stable(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode()).hexdigest()[:16]


def rca_contract(task: str) -> dict[str, Any]:
    goal = str(task).strip()
    if not goal:
        raise ValueError("RCA task cannot be empty")
    return {
        "version": VERSION,
        "goal": goal,
        "mode": "analysis-only",
        "patch_allowed": False,
        "required_outputs": ["timeline", "observations", "flow", "hypotheses", "evidence", "contradictions", "unknowns", "root_cause", "confidence", "follow_up"],
    }


def finding(kind: str, text: str, evidence_ids: list[str] | None = None, confidence: str = "medium") -> dict[str, Any]:
    if kind not in {"fact", "inference", "unknown", "recommendation"}:
        raise ValueError("unsupported finding kind")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError("unsupported confidence")
    value = str(text).strip()
    if not value:
        raise ValueError("finding text cannot be empty")
    return {"id": f"finding-{_stable((kind, value, evidence_ids or []))}", "kind": kind, "text": value, "evidence_ids": sorted(set(evidence_ids or [])), "confidence": confidence}


def hypothesis(text: str, evidence_for: list[str] | None = None, evidence_against: list[str] | None = None, confidence: str = "medium") -> dict[str, Any]:
    if confidence not in {"high", "medium", "low"}:
        raise ValueError("unsupported confidence")
    return {
        "id": f"hyp-{_stable(text)}",
        "text": str(text).strip(),
        "evidence_for": sorted(set(evidence_for or [])),
        "evidence_against": sorted(set(evidence_against or [])),
        "confidence": confidence,
    }


def report(task: str, timeline: list[dict[str, Any]], observations: list[dict[str, Any]], flow: list[dict[str, Any]], hypotheses: list[dict[str, Any]], evidence: list[dict[str, Any]], contradictions: list[str], unknowns: list[str], root_cause: dict[str, Any] | None = None, follow_up: list[str] | None = None) -> dict[str, Any]:
    root = root_cause or {"status": "unproven", "statement": "", "evidence_ids": [], "confidence": "low"}
    if root.get("status") not in {"proven", "probable", "unproven"}:
        raise ValueError("invalid root cause status")
    return {
        "version": VERSION,
        "mode": "analysis-only",
        "patch_allowed": False,
        "task": str(task).strip(),
        "timeline": timeline,
        "observations": observations,
        "flow": flow,
        "hypotheses": hypotheses,
        "evidence": evidence,
        "contradictions": contradictions,
        "unknowns": unknowns,
        "root_cause": root,
        "follow_up": list(follow_up or []),
    }
