#!/usr/bin/env python3
"""Canonical requirement-to-evidence traceability for engineering work."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
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
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def normalize_requirements(source: dict[str, Any] | None, *, fallback_goal: str = "") -> list[dict[str, Any]]:
    """Normalize explicit requirements and preserve missing acceptance criteria as gaps."""
    source = source if isinstance(source, dict) else {}
    raw = source.get("requirements")
    if raw is None:
        raw = source.get("acceptance_criteria")
    if raw is None:
        raw = []
    if isinstance(raw, str):
        raw = [raw]
    result: list[dict[str, Any]] = []
    for item in _list(raw):
        if isinstance(item, dict):
            requirement = _text(item.get("requirement") or item.get("description") or item.get("text"))
            rid = _text(item.get("requirement_id") or item.get("id"))
            criteria = item.get("acceptance_criteria") or item.get("criteria") or item.get("acceptance") or []
            design = _text(item.get("design_pointer") or item.get("design"))
            code = _text(item.get("code_pointer") or item.get("implementation_pointer") or item.get("code"))
            test = _text(item.get("test_pointer") or item.get("test"))
            evidence = _text(item.get("evidence_pointer") or item.get("evidence"))
        else:
            requirement, rid, criteria = _text(item), "", []
            design = code = test = evidence = ""
        if not requirement:
            continue
        rid = rid or _id(requirement, "REQ")
        if isinstance(criteria, str):
            criteria = [criteria]
        criteria_list = [_text(x.get("text") if isinstance(x, dict) else x) for x in _list(criteria)]
        criteria_list = [x for x in criteria_list if x]
        result.append({"requirement_id": rid, "requirement": requirement, "acceptance_criteria": criteria_list,
                       "design_pointer": design, "code_pointer": code, "test_pointer": test, "evidence_pointer": evidence})
    # A Jira item is itself an explicit requirement reference. Do not manufacture an acceptance criterion.
    if not result and fallback_goal and _text(source.get("jira_id")):
        result.append({"requirement_id": _id(fallback_goal, "REQ"), "requirement": fallback_goal, "acceptance_criteria": [],
                       "design_pointer": "", "code_pointer": "", "test_pointer": "", "evidence_pointer": ""})
    return result


def build_requirement_traces(*, requirements: Iterable[dict[str, Any]], regression_ids: Iterable[str] = (), replay: Iterable[dict[str, Any]] = (), default_evidence: str = "") -> list[RequirementTrace]:
    replay_rows = [x for x in replay if isinstance(x, dict)]
    replay_ids = [_text(x.get("replay_id") or x.get("id")) for x in replay_rows if _text(x.get("replay_id") or x.get("id"))]
    replay_status = "passed" if replay_rows and all(bool(x.get("passed")) for x in replay_rows) else ("failed" if replay_rows else "not-run")
    regressions = sorted({_text(x) for x in regression_ids if _text(x)})
    traces: list[RequirementTrace] = []
    for item in requirements:
        rid = _text(item.get("requirement_id"))
        criteria = _list(item.get("acceptance_criteria")) or [""]
        for index, criterion in enumerate(criteria, 1):
            cid = _text(criterion.get("criterion_id") if isinstance(criterion, dict) else "") or f"{rid}.AC-{index}"
            text = _text(criterion.get("text") if isinstance(criterion, dict) else criterion)
            design, code, test = _text(item.get("design_pointer")), _text(item.get("code_pointer")), _text(item.get("test_pointer"))
            evidence = _text(item.get("evidence_pointer") or default_evidence)
            complete = bool(text and design and code and test and evidence)
            if complete and (not replay_rows or replay_status == "passed"):
                status = "covered"
            elif any((text, design, code, test, evidence)):
                status = "partially-covered"
            else:
                status = "uncovered"
            missing = [name for name, value in (("acceptance criterion", text), ("design", design), ("code", code), ("test", test), ("evidence", evidence)) if not value]
            if replay_status == "failed":
                missing.append("replay")
            gap = ", ".join(missing)
            traces.append(RequirementTrace(rid, cid, _text(item.get("requirement")), text, design, code, test, evidence,
                                           regressions, replay_ids, replay_status, status, gap))
    return traces


def persist_requirement_traceability(root: Path, work_id: str, *, jira_id: str = "", work_type: str = "", requirements: Iterable[dict[str, Any]] = (), regression_ids: Iterable[str] = (), replay: Iterable[dict[str, Any]] = (), evidence: Iterable[dict[str, Any]] = (), source: str = "") -> dict[str, Any]:
    root = Path(root)
    evidence_rows = [dict(x) for x in evidence if isinstance(x, dict)]
    replay_rows = [x for x in replay if isinstance(x, dict)]
    traces = build_requirement_traces(requirements=requirements, regression_ids=regression_ids, replay=replay_rows, default_evidence=source)
    payload = {
        "schema_version": TRACEABILITY_SCHEMA_VERSION,
        "work_id": _text(work_id), "jira_id": _text(jira_id), "work_type": _text(work_type), "generated_at": int(time.time()),
        "chain": "Jira/Requirement -> Acceptance Criterion -> Design -> Code change -> Test -> Evidence -> Regression -> Replay result -> WorkReport",
        "requirements": [asdict(x) for x in traces],
        "regression_ids": sorted({_text(x) for x in regression_ids if _text(x)}),
        "replay": replay_rows, "evidence": evidence_rows, "source": _text(source),
    }
    payload["coverage"] = {"total_criteria": len(traces), "covered": sum(x.status == "covered" for x in traces),
                            "partial": sum(x.status == "partially-covered" for x in traces), "uncovered": sum(x.status == "uncovered" for x in traces),
                            "residual_gaps": [x.residual_gap for x in traces if x.residual_gap]}
    out = root / ".ai-harness" / "reports" / "traceability"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{work_id}-requirements.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
