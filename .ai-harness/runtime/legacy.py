#!/usr/bin/env python3
"""Legacy-aware analysis primitives for undocumented flows and shape-dependent behavior."""
from __future__ import annotations

import hashlib
import json
from typing import Any

VERSION = "1.1"


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def normalize_shape(value: Any, depth: int = 0, max_depth: int = 6) -> Any:
    """Return a bounded structural fingerprint without retaining payload values."""
    if depth >= max_depth:
        return "<depth-limit>"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (bytes, bytearray)):
        return "bytes"
    if isinstance(value, dict):
        return {str(k): normalize_shape(v, depth + 1, max_depth) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        members = [normalize_shape(v, depth + 1, max_depth) for v in list(value)[:16]]
        return {"type": "array", "sample_size": len(value), "members": members}
    return type(value).__name__


def shape_fingerprint(value: Any) -> dict[str, Any]:
    shape = normalize_shape(value)
    serialized = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    return {"id": stable_id("shape", serialized), "version": VERSION, "shape": shape}


def compare_shapes(left: Any, right: Any) -> dict[str, Any]:
    first, second = shape_fingerprint(left), shape_fingerprint(right)
    return {"compatible": first["shape"] == second["shape"], "left_id": first["id"], "right_id": second["id"], "left": first["shape"], "right": second["shape"]}


def flow_step(component: str, operation: str, inputs: list[str] | None = None, outputs: list[str] | None = None, conditions: list[str] | None = None, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {"id": stable_id("flow", "|".join((component, operation, repr(inputs or []), repr(outputs or []), repr(conditions or [])))), "component": component, "operation": operation, "inputs": inputs or [], "outputs": outputs or [], "conditions": conditions or [], "evidence_ids": sorted(set(evidence_ids or []))}


def variant(component: str, condition: str, shape_id: str | None = None, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {"id": stable_id("variant", "|".join((component, condition, shape_id or ""))), "component": component, "condition": condition, "shape_id": shape_id, "evidence_ids": sorted(set(evidence_ids or []))}


def impact_closure(edges: list[dict[str, Any]], roots: list[str], max_nodes: int = 500) -> dict[str, Any]:
    """Bounded transitive closure for relationship analysis; cycles are handled safely."""
    if max_nodes <= 0 or max_nodes > 5000:
        raise ValueError("max_nodes must be between 1 and 5000")
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        src, dst = str(edge.get("source", "")), str(edge.get("target", ""))
        if src and dst:
            adjacency.setdefault(src, set()).add(dst)
    seen: set[str] = set(roots)
    queue = list(dict.fromkeys(roots))
    while queue and len(seen) < max_nodes:
        current = queue.pop(0)
        for nxt in sorted(adjacency.get(current, ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
                if len(seen) >= max_nodes:
                    break
    return {"roots": list(dict.fromkeys(roots)), "nodes": sorted(seen), "truncated": bool(queue), "max_nodes": max_nodes}


def evidence_path(path: list[dict[str, Any]], evidence_ids: list[str] | None = None) -> dict[str, Any]:
    """Build a bounded, evidence-linked runtime path without asserting undocumented behavior."""
    if len(path) > 1000:
        raise ValueError("path exceeds safe bound")
    return {"version": VERSION, "steps": path, "evidence_ids": sorted(set(evidence_ids or [])), "complete": bool(path)}


def shape_variants(observations: list[dict[str, Any]], max_variants: int = 100) -> dict[str, Any]:
    """Group observed flow variants by structural data shape; values are never persisted."""
    if max_variants <= 0 or max_variants > 1000:
        raise ValueError("max_variants must be between 1 and 1000")
    groups: dict[str, dict[str, Any]] = {}
    for item in observations[:5000]:
        component = str(item.get("component", "unknown"))
        condition = str(item.get("condition", "observed"))
        fingerprint = shape_fingerprint(item.get("data")).get("id") if "data" in item else "shape-unknown"
        key = f"{component}|{condition}|{fingerprint}"
        if key not in groups and len(groups) >= max_variants:
            break
        groups.setdefault(key, {"component": component, "condition": condition, "shape_id": fingerprint, "count": 0})["count"] += 1
    return {"version": VERSION, "variants": sorted(groups.values(), key=lambda x: (x["component"], x["condition"], x["shape_id"]))}
