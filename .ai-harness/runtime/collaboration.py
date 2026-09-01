#!/usr/bin/env python3
"""Shared collaboration fabric for handoffs, memory exchange, and evidence lineage."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

VERSION = "1.0"
SAFE_MEMORY_KINDS = {"fact", "evidence", "decision", "do", "dont", "risk", "handoff", "unknown"}
IMMUTABLE_MEMORY_KINDS = {"intent", "guardrail", "policy"}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _normalize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def create_memory_item(*, kind: str, text: str, source: str, evidence_ids: list[str] | None = None,
                       confidence: float = 0.0, run_id: str | None = None,
                       intent_digest: str | None = None, parents: list[str] | None = None,
                       task_scope: str | None = None) -> dict[str, Any]:
    kind = str(kind).strip().lower()
    if kind not in SAFE_MEMORY_KINDS | IMMUTABLE_MEMORY_KINDS:
        raise ValueError(f"unsupported memory kind: {kind}")
    text = str(text).strip()
    if not text:
        raise ValueError("memory text is required")
    confidence = max(0.0, min(1.0, float(confidence)))
    evidence_ids = sorted(set(str(x).strip() for x in (evidence_ids or []) if str(x).strip()))
    parents = sorted(set(str(x).strip() for x in (parents or []) if str(x).strip()))
    payload = {
        "version": VERSION, "kind": kind, "text": text, "source": str(source).strip(),
        "evidence_ids": evidence_ids, "confidence": confidence, "run_id": run_id,
        "intent_digest": intent_digest, "parents": parents, "task_scope": task_scope,
    }
    payload["id"] = _stable_id("mem", _normalize({k: v for k, v in payload.items() if k != "version"}))
    payload["created_at"] = int(time.time())
    return payload


def validate_memory_item(item: dict[str, Any], *, expected_intent_digest: str | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    kind = item.get("kind")
    if kind not in SAFE_MEMORY_KINDS | IMMUTABLE_MEMORY_KINDS:
        reasons.append("unsupported_kind")
    if not str(item.get("text", "")).strip():
        reasons.append("missing_text")
    if expected_intent_digest and item.get("intent_digest") and item.get("intent_digest") != expected_intent_digest:
        reasons.append("intent_mismatch")
    if kind in {"fact", "evidence", "decision"} and not item.get("evidence_ids"):
        reasons.append("missing_evidence")
    return {"passed": not reasons, "reasons": reasons}


def memory_graph(items: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = {}
    edges = []
    for item in items:
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        nodes[item_id] = dict(item)
        for parent in item.get("parents", []) or []:
            if str(parent).strip():
                edges.append({"from": str(parent), "to": item_id, "relation": "derived_from"})
        for evidence_id in item.get("evidence_ids", []) or []:
            edges.append({"from": str(evidence_id), "to": item_id, "relation": "supports"})
    return {"version": VERSION, "nodes": nodes, "edges": edges}


def build_handoff(*, intent: dict[str, Any], phase: str, from_component: str,
                  to_component: str, findings: list[dict[str, Any]] | None = None,
                  decisions: list[dict[str, Any]] | None = None,
                  open_risks: list[dict[str, Any]] | None = None,
                  next_actions: list[str] | None = None) -> dict[str, Any]:
    digest = str(intent.get("intent_digest", "")).strip()
    if not digest:
        raise ValueError("intent contract with intent_digest is required")
    findings = list(findings or [])
    decisions = list(decisions or [])
    open_risks = list(open_risks or [])
    next_actions = [str(x).strip() for x in (next_actions or []) if str(x).strip()]
    packet = {
        "version": VERSION,
        "id": _stable_id("handoff", _normalize({
            "intent_digest": digest, "phase": phase, "from": from_component, "to": to_component,
            "findings": findings, "decisions": decisions, "open_risks": open_risks, "next_actions": next_actions,
        })),
        "intent_digest": digest,
        "phase": str(phase),
        "from_component": str(from_component),
        "to_component": str(to_component),
        "findings": findings,
        "decisions": decisions,
        "open_risks": open_risks,
        "next_actions": next_actions,
        "created_at": int(time.time()),
    }
    return packet


def validate_handoff(packet: dict[str, Any], *, expected_intent_digest: str,
                     allowed_scope: set[str] | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    if packet.get("intent_digest") != expected_intent_digest:
        reasons.append("intent_mismatch")
    if not packet.get("from_component") or not packet.get("to_component"):
        reasons.append("missing_component")
    if allowed_scope is not None:
        for item in packet.get("findings", []) + packet.get("decisions", []) + packet.get("open_risks", []):
            scope = item.get("task_scope") if isinstance(item, dict) else None
            if scope and scope not in allowed_scope:
                reasons.append("scope_violation")
                break
    return {"passed": not reasons, "reasons": reasons}


def persist_handoff(root: Path, packet: dict[str, Any]) -> Path:
    """Persist a validated handoff so another session or agent can resume safely."""
    digest = str(packet.get("intent_digest", "")).strip()
    if not digest:
        raise ValueError("handoff intent_digest is required")
    path = Path(root) / ".ai-harness" / "state" / "handoffs" / f"{packet.get("id", "handoff")}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return path


def load_handoff(path: Path, *, expected_intent_digest: str,
                 allowed_scope: set[str] | None = None) -> dict[str, Any]:
    packet = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_handoff(packet, expected_intent_digest=expected_intent_digest, allowed_scope=allowed_scope)
    if not result["passed"]:
        raise ValueError("invalid handoff: " + ",".join(result["reasons"]))
    return packet


def shared_memory(root: Path, *, intent_digest: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    root = Path(root)
    learn = root / ".ai-harness" / "learning"
    paths = [learn / "patterns.jsonl", learn / "regression-events.jsonl", learn / "skill-proposals.jsonl"]
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and (not intent_digest or not row.get("intent_digest") or row.get("intent_digest") == intent_digest):
                rows.append(row)
    rows.sort(key=lambda x: (-float(x.get("confidence", 0)), -int(x.get("last_seen_at", x.get("reported_at", 0))), str(x.get("id", ""))))
    return rows[:max(0, min(500, int(limit)))]


def collaboration_snapshot(root: Path, *, intent: dict[str, Any], component: str,
                           phase: str, evidence: list[dict[str, Any]] | None = None,
                           findings: list[dict[str, Any]] | None = None,
                           open_risks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    digest = str(intent.get("intent_digest", ""))
    memory = shared_memory(root, intent_digest=digest)
    graph_items = []
    for row in evidence or []:
        if isinstance(row, dict):
            graph_items.append(create_memory_item(kind="evidence", text=str(row.get("text", row.get("id", "evidence"))),
                source=component, evidence_ids=[str(row.get("id", ""))] if row.get("id") else [],
                confidence=float(row.get("confidence", 0)), intent_digest=digest, task_scope=phase))
    for row in findings or []:
        if isinstance(row, dict):
            graph_items.append(create_memory_item(kind="fact", text=str(row.get("text", row.get("summary", "finding"))),
                source=component, evidence_ids=list(row.get("evidence_ids", [])), confidence=float(row.get("confidence", 0)),
                intent_digest=digest, task_scope=phase))
    return {
        "version": VERSION,
        "intent_digest": digest,
        "component": component,
        "phase": phase,
        "shared_memory": memory,
        "graph": memory_graph(graph_items),
        "open_risks": list(open_risks or []),
    }
