#!/usr/bin/env python3
"""Execution controls: scope fencing, checkpoints, chunking, and context integrity."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

VERSION = "1.2"


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def normalize_scope(paths: list[str] | None) -> list[str]:
    return sorted({str(p).replace("\\", "/").strip("/") for p in (paths or []) if str(p).strip()})


def path_in_scope(path: str, roots: list[str]) -> bool:
    value = path.replace("\\", "/").strip("/")
    return any(root in ("", ".") or value == root or value.startswith(root.rstrip("/") + "/") for root in roots)


def scope_check(changed_paths: list[str], allowed_paths: list[str] | None = None, protected_paths: list[str] | None = None) -> dict[str, Any]:
    allowed = normalize_scope(allowed_paths) or ["."]
    protected = normalize_scope(protected_paths)
    outside = sorted(p for p in changed_paths if not path_in_scope(p, allowed))
    protected_hits = sorted(p for p in changed_paths if any(path_in_scope(p, [root]) for root in protected))
    return {"allowed_paths": allowed, "protected_paths": protected, "outside_scope": outside, "protected_changes": protected_hits, "passed": not outside and not protected_hits}


def task_chunks(task: str, *, max_chunks: int = 8, complexity: int | None = None) -> list[dict[str, str]]:
    words = len(re.findall(r"\w+", task))
    text = task.lower()
    signals = sum(token in text for token in ("migration", "api", "security", "legacy", "multiple", "across", "data shape", "end-to-end"))
    score = max(1, min(10, complexity if complexity is not None else 1 + words // 25 + signals))
    if score <= 2:
        return [{"id": "chunk-1", "goal": task.strip(), "verify": "focused repository-native verification"}]
    labels = ["understand", "flow-impact", "implementation", "verification"]
    if score >= 7:
        labels[2:2] = ["data-shapes", "compatibility"]
    return [{"id": f"chunk-{i + 1}", "goal": label, "verify": "checkpoint before next chunk"} for i, label in enumerate(labels[:max_chunks])]


def context_integrity(task: str, contract: dict[str, Any], recent_output: str, key_instructions: list[str], max_output_chars: int = 12000) -> dict[str, Any]:
    text = recent_output[-max_output_chars:].lower()
    goal = str(contract.get("goal", task)).strip().lower()
    instructions = [str(x).strip() for x in key_instructions if str(x).strip()]

    def instruction_present(item: str) -> bool:
        terms = [term for term in re.findall(r"[a-z0-9_]{3,}", item.lower()) if term not in {"the", "and", "with"}]
        if not terms:
            return True
        matched = 0
        for term in terms:
            stem = term[: max(3, len(term) - 2)]
            if term in text or stem in text:
                matched += 1
        return matched / len(terms) >= 0.6

    missing = [item for item in instructions if not instruction_present(item)]
    terms = [x for x in re.findall(r"[a-z0-9_]{4,}", goal) if x not in {"with", "that", "this", "must"}][:30]
    overlap = sum(term in text for term in terms) / max(1, len(terms))
    rot = len(missing) / max(1, len(instructions)) if instructions else 0.0
    return {"context_rot_score": round(rot, 4), "goal_overlap": round(overlap, 4), "missing_key_instructions": missing, "context_rot": rot >= 0.5, "guardrail_loss": bool(instructions) and rot >= 0.67}


def unsupported_claims(text: str, evidence_markers: list[str] | None = None) -> list[str]:
    markers = [str(x).lower() for x in (evidence_markers or [])]
    claims: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if clean and any(re.search(pattern, clean, re.I) for pattern in (r"\bverified\b", r"\bconfirmed\b", r"\bproven\b", r"\bno regression\b")) and not any(marker in clean.lower() for marker in markers):
            claims.append(clean)
    return claims[:50]


def guard_check(task: str, contract: dict[str, Any], output: str, key_instructions: list[str], changed_paths: list[str], allowed_paths: list[str] | None = None, protected_paths: list[str] | None = None, evidence_markers: list[str] | None = None) -> dict[str, Any]:
    integrity = context_integrity(task, contract, output, key_instructions)
    scope = scope_check(changed_paths, allowed_paths, protected_paths)
    claims = unsupported_claims(output, evidence_markers)
    return {"version": VERSION, "passed": scope["passed"] and not integrity["guardrail_loss"] and not claims, "scope": scope, "integrity": integrity, "unsupported_claims": claims}


def checkpoint(run_id: str, phase: str, index: int, total: int, state: dict[str, Any], changed_paths: list[str], output: str, key_instructions: list[str], allowed_paths: list[str] | None = None, protected_paths: list[str] | None = None) -> dict[str, Any]:
    scope = scope_check(changed_paths, allowed_paths, protected_paths)
    return {"version": VERSION, "run_id": run_id, "phase": phase, "index": index, "total": total, "state_digest": stable_digest(state), "output_digest": stable_digest(output), "changed_paths": sorted(set(changed_paths)), "scope": scope, "next": "continue" if scope["passed"] else "stop_and_review_scope"}


def save_checkpoint(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
