#!/usr/bin/env python3
"""Canonical requirement-to-evidence traceability for engineering work."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import time

TRACEABILITY_SCHEMA_VERSION = "2.0"


@dataclass(frozen=True)
class RequirementTrace:
    requirement_id: str
    criterion_id: str
    requirement: str = ""
    acceptance_criterion: str = ""
    design_pointer: str = ""
    code_pointer: str = ""
    test_pointer: str = ""
    evidence_pointer: str = ""
    regression_ids: list[str] = field(default_factory=list)
    replay_ids: list[str] = field(default_factory=list)
    replay_status: str = "not-run"
    status: str = "uncovered"
    residual_gap: str = ""


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _id(value: str, prefix: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def normalize_requirements(source: dict[str, Any] | None, *, fallback_goal: str = "") -> list[dict[str, Any]]:
    """Normalize only explicit requirement/acceptance data; never invent acceptance criteria."""
    source = source if isinstance(source, dict) else {}
    raw = source.get("requirements")
    if raw is None:
        raw = source.get("acceptance_criteria")
    if raw is None:
        raw = []
    if isinstance(raw, str):
        raw = [raw]
    result: list[dict[str, Any]] = []
    for index, item in enumerate(_list(raw), 1):
        if isinstance(item, dict):
            requirement = _text(item.get("requirement") or item.get("description") or item.get("text"))
            rid = _text(item.get("requirement_id") or item.get("id"))
            criteria = item.get("acceptance_criteria") or item.get("criteria") or item.get("acceptance") or []
            design = _text(item.get("design_pointer") or item.get("design"))
            code = _text(item.get("code_pointer") or item.get("implementation_pointer") or item.get("code"))
            test = _text(item.get("test_pointer") or item.get("test"))
            evidence = _text(item.get("evidence_pointer") or item.get("evidence"))
        else:
            requirement = _text(item)
            rid = ""
            criteria = []
            design = code = test = evidence = ""
        if not requirement:
            continue
        rid = rid or _id(requirement, "REQ")
        if isinstance(criteria, str):
            criteria = [criteria]
        criteria_list = [_text(x.get("text") if isinstance(x, dict) else x) for x in _list(criteria)]
        criteria_list = [x for x in criteria_list if x]
        if not criteria_list:
            criteria_list = [requirement] if source.get("requirements") is not None and source.get("acceptance_criteria") is None else []
        result.append({
            "requirement_id": rid,
            "requirement": requirement,
            "acceptance_criteria": criteria_list,
            "design_pointer": design,
            "code_pointer": code,
            "test_pointer": test,
            "evidence_pointer": evidence,
        })
    if not result and fallback_goal and source.get("requirements") is not None:
        result.append({"requirement_id": _id(fallback_goal, "REQ"), "requirement": fallback_goal, "acceptance_criteria": []})
    return result


def build_requirement_traces(*, requirements: Iterable[dict[str, Any]], regression_ids: Iterable[str] = (), replay: Iterable[dict[str, Any]] = (), default_evidence: str = "") -> list[RequirementTrace]:
    replay_rows = [x for x in replay if isinstance(x, dict)]
    replay_ids = [_text(x.get("replay_id") or x.get("id")) for x in replay_rows if _text(x.get("replay_id") or x.get("id"))]
    replay_status = "passed" if replay_rows and all(bool(x.get("passed")) for x in replay_rows) else ("failed" if replay_rows else "not-run")
    regressions = sorted({_text(x) for x in regression_ids if _text(x)})
    traces: list[RequirementTrace] = []
    for item in requirements:
        rid = _text(item.get("requirement_id"))
        criteria = _list(item.get("acceptance_criteria"))
        for index, criterion in enumerate(criteria or [""] , 1):
            cid = _text(criterion.get("criterion_id") if isinstance(criterion, dict) else "") or f"{rid}.AC-{index}"
            text = _text(criterion.get("text") if isinstance(criterion, dict) else criterion)
            design = _text(item.get("design_pointer"))
            code = _text(item.get("code_pointer"))
            test = _text(item.get("test_pointer"))
            evidence = _text(item.get("evidence_pointer") or default_evidence)
            complete = bool(design and code and test and evidence)
            status = "covered" if complete and (not replay_rows or replay_status == "passed") else ("partially-covered" if any((design, code, test, evidence)) else "uncovered")
            gap = "" if status == "covered" else ", ".join(name for name, value in (("design", design), ("code", code), ("test", test), ("evidence", evidence)) if not value) or ("replay failed" if replay_status == "failed" else "")
            traces.append(RequirementTrace(rid, cid, _text(item.get("requirement")), text, design, code, test, evidence, regressions, replay_ids, replay_status, status, gap))
    return traces


def persist_requirement_traceability(root: Path, work_id: str, *, jira_id: str = "", work_type: str = "", requirements: Iterable[dict[str, Any]] = (), regression_ids: Iterable[str] = (), replay: Iterable[dict[str, Any]] = (), evidence: Iterable[dict[str, Any]] = (), source: str = "") -> dict[str, Any]:
    root = Path(root)
    evidence_rows = [dict(x) for x in evidence if isinstance(x, dict)]
    traces = build_requirement_traces(requirements=requirements, regression_ids=regression_ids, replay=replay, default_evidence=source)
    payload = {
        "schema_version": TRACEABILITY_SCHEMA_VERSION,
        "work_id": _text(work_id),
        "jira_id": _text(jira_id),
        "work_type": _text(work_type),
        "generated_at": int(time.time()),
        "chain": "Jira/Requirement -> Acceptance Criterion -> Design -> Code change -> Test -> Evidence -> Regression -> Replay result -> WorkReport",
        "requirements": [asdict(x) for x in traces],
        "regression_ids": sorted({_text(x) for x in regression_ids if _text(x)}),
        "replay": replay_rows if (replay_rows := [x for x in replay if isinstance(x, dict)]) else [],
        "evidence": evidence_rows,
        "source": _text(source),
    }
    payload["coverage"] = {
        "total_criteria": len(traces),
        "covered": sum(x.status == "covered" for x in traces),
        "partial": sum(x.status == "partially-covered" for x in traces),
        "uncovered": sum(x.status == "uncovered" for x in traces),
        "residual_gaps": [x.residual_gap for x in traces if x.residual_gap],
    }
    out = root / ".ai-harness" / "reports" / "traceability"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{work_id}-requirements.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
