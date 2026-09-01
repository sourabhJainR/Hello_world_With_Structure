#!/usr/bin/env python3
"""Bounded, evidence-driven learning for durable do/don't patterns and skill refinement proposals."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

VERSION = "1.1"
IMMUTABLE_TOPICS = {"security", "permissions", "approval", "dependency_allowlist", "architecture_policy", "repository_rules", "executable_harness"}


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _compact(text: str, limit: int = 600) -> str:
    value = str(text).strip()
    return value if len(value) <= limit else value[: max(1, limit - 20)] + " ...[trimmed]"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try: value = json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(value, dict): rows.append(value)
    return rows


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def _normalize(text: str) -> str: return re.sub(r"\s+", " ", str(text).strip().lower())


def _extract_candidates(manifest: dict[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    review_path = run_dir / "review.output.md"
    review = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    outcome = manifest.get("outcome", {}) if isinstance(manifest.get("outcome"), dict) else {}
    validation = manifest.get("validation", {}) if isinstance(manifest.get("validation"), dict) else {}
    success = bool(validation.get("passed", True)) and manifest.get("status") == "completed"
    candidates = []
    for line in review.splitlines():
        clean = line.strip(" -#\t")
        if not clean: continue
        lower = clean.lower(); kind = None
        if any(t in lower for t in ("avoid:", "do not:", "don't:", "never:", "regression warning", "would break")): kind = "dont"
        elif any(t in lower for t in ("prefer:", "do:", "recommend:", "lesson:", "keep:", "works well")): kind = "do"
        if kind:
            topic = "general"
            for candidate_topic in IMMUTABLE_TOPICS:
                aliases = {candidate_topic, candidate_topic.replace("_", " ")}
                if any(alias in lower for alias in aliases):
                    topic = candidate_topic
                    break
            candidates.append({"kind": kind, "topic": topic, "text": _compact(clean), "success": success, "source_run": manifest.get("run_id"), "intent_digest": manifest.get("intent_digest"), "event_type": "task-completion"})
    for finding in outcome.get("review_findings", []) if isinstance(outcome.get("review_findings"), list) else []:
        text = _compact(str(finding))
        if text: candidates.append({"kind": "dont", "topic": "regression", "text": text, "success": success, "source_run": manifest.get("run_id"), "intent_digest": manifest.get("intent_digest"), "event_type": "task-completion"})
    return candidates


def _aggregate(existing, candidates, now):
    records = {}
    for row in existing:
        key = _normalize(str(row.get("text", "")))
        if key: records[key] = dict(row)
    for candidate in candidates:
        key = _normalize(candidate["text"])
        if not key: continue
        row = records.setdefault(key, {"id": stable_id("learn", key), "version": VERSION, "kind": candidate["kind"], "topic": candidate["topic"], "text": candidate["text"], "observations": 0, "successes": 0, "contradictions": 0, "confidence": 0.0, "status": "candidate", "created_at": now, "last_seen_at": now, "source_runs": []})
        row["observations"] = int(row.get("observations", 0)) + 1
        row["successes"] = int(row.get("successes", 0)) + (1 if candidate.get("success") else 0)
        row["last_seen_at"] = now
        runs = list(row.get("source_runs", [])); source_run = candidate.get("source_run")
        if source_run and source_run not in runs: runs.append(source_run)
        row["source_runs"] = runs[-20:]
        if candidate["kind"] != row.get("kind"): row["contradictions"] = int(row.get("contradictions", 0)) + 1
        observations = max(1, int(row["observations"])); success_rate = int(row["successes"]) / observations; contradictions = int(row.get("contradictions", 0))
        row["success_rate"] = round(success_rate, 3); row["confidence"] = round(max(0.0, success_rate - min(0.5, contradictions * 0.15)), 3)
    return list(records.values())


def _promote(records, *, min_observations, min_success_rate, stale_after_days, now):
    stale_seconds = stale_after_days * 86400
    for row in records:
        age = max(0, now - int(row.get("last_seen_at", now))); immutable = row.get("topic") in IMMUTABLE_TOPICS
        if age > stale_seconds: row["status"] = "deprecated"
        elif int(row.get("contradictions", 0)) > 0 and int(row.get("observations", 0)) < min_observations * 2: row["status"] = "candidate"
        elif int(row.get("observations", 0)) >= min_observations and float(row.get("success_rate", 0)) >= min_success_rate and float(row.get("confidence", 0)) >= min_success_rate: row["status"] = "trusted"
        else: row["status"] = "candidate"
        row["immutable"] = immutable; row["application"] = "advisory-only" if immutable else "context-advisory"


def evolve_run(run_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists(): return {"status": "skipped", "reason": "missing-manifest"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")); now = int(time.time()); learning = config.get("learning", {}); root = run_dir.parents[2] if len(run_dir.parents) > 2 else Path("."); learn_dir = root / ".ai-harness" / "learning"; registry_path = learn_dir / "patterns.jsonl"
    existing = _read_jsonl(registry_path); candidates = _extract_candidates(manifest, run_dir); records = _aggregate(existing, candidates, now)
    _promote(records, min_observations=int(learning.get("min_observations_for_promotion", 3)), min_success_rate=float(learning.get("min_success_rate_for_promotion", 0.75)), stale_after_days=int(learning.get("stale_after_days", 120)), now=now)
    records.sort(key=lambda row: (-float(row.get("confidence", 0)), -int(row.get("last_seen_at", 0)), str(row.get("id", "")))); records = records[:int(learning.get("max_memory_items", 250))]
    learn_dir.mkdir(parents=True, exist_ok=True); tmp = registry_path.with_suffix(".tmp"); tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"); tmp.replace(registry_path)
    proposal_path = learn_dir / "skill-proposals.jsonl"; existing_ids = {item.get("id") for item in _read_jsonl(proposal_path)}
    for row in records:
        if row.get("status") != "trusted" or row.get("immutable"): continue
        proposal = {"id": stable_id("skill-proposal", row["id"]), "version": VERSION, "source_pattern_id": row["id"], "kind": row["kind"], "topic": row["topic"], "text": row["text"], "status": "candidate", "requires_eval": True, "requires_review": True, "executable": False}
        if proposal["id"] not in existing_ids: _append_jsonl(proposal_path, proposal); existing_ids.add(proposal["id"])
    trusted = sum(1 for row in records if row.get("status") == "trusted"); deprecated = sum(1 for row in records if row.get("status") == "deprecated")
    return {"status": "evolved", "observed": len(candidates), "patterns": len(records), "trusted": trusted, "deprecated": deprecated, "proposal_count": len(existing_ids)}


def record_reported_regression(root: Path, *, original_run_id: str, intent_digest: str, summary: str, evidence_ids: list[str], rca_status: str = "unproven") -> dict[str, Any]:
    """Record a later regression/miss as learning input without modifying product code."""
    if rca_status not in {"unproven", "probable", "proven"}: raise ValueError("invalid RCA status")
    summary = _compact(summary, 1000)
    if not summary: raise ValueError("regression summary is required")
    now = int(time.time()); root = Path(root); learn_dir = root / ".ai-harness" / "learning"; learn_dir.mkdir(parents=True, exist_ok=True)
    record = {"id": stable_id("regression", f"{original_run_id}|{summary}|{intent_digest}"), "version": VERSION, "event_type": "reported-regression", "reported_at": now, "original_run_id": str(original_run_id), "intent_digest": str(intent_digest), "summary": summary, "evidence_ids": sorted(set(str(x) for x in evidence_ids if str(x).strip())), "rca_status": rca_status, "patch_applied": False, "learning_status": "candidate"}
    _append_jsonl(learn_dir / "regression-events.jsonl", record)
    if record["evidence_ids"]:
        candidate = {"kind": "dont", "topic": "regression", "text": summary, "success": False, "source_run": original_run_id, "intent_digest": intent_digest, "event_type": "reported-regression"}
        registry = _read_jsonl(learn_dir / "patterns.jsonl"); records = _aggregate(registry, [candidate], now)
        _promote(records, min_observations=3, min_success_rate=0.75, stale_after_days=120, now=now)
        tmp = learn_dir / "patterns.tmp"; tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"); tmp.replace(learn_dir / "patterns.jsonl")
    return record


def trusted_advice(root: Path, topic: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    rows = _read_jsonl(root / ".ai-harness" / "learning" / "patterns.jsonl"); active = [row for row in rows if row.get("status") == "trusted" and row.get("application") in ("context-advisory", "advisory-only")]
    if topic: active = [row for row in active if row.get("topic") in (topic, "general", "regression")]
    active.sort(key=lambda row: (-float(row.get("confidence", 0)), -int(row.get("last_seen_at", 0)), str(row.get("id", "")))); return active[:max(0, min(100, int(limit)))]
