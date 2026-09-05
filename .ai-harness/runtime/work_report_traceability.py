#!/usr/bin/env python3
"""Bridge engineering reports, requirements, verified regression knowledge, planning context and replay provenance."""
from __future__ import annotations
from html import escape
from pathlib import Path
from typing import Any
import json
import time
try:
    from .learning_controller import LearningController
    from .requirement_traceability import normalize_requirements, persist_requirement_traceability
    from .work_report import WorkReport
except ImportError:
    from learning_controller import LearningController
    from requirement_traceability import normalize_requirements, persist_requirement_traceability
    from work_report import WorkReport

TRACEABILITY_VERSION = "2.0"

def _items(value: Any) -> list[Any]: return value if isinstance(value, list) else []
def _text(value: Any) -> str: return str(value).strip() if value is not None else ""

def _knowledge_item(raw: Any, *, task_family: str, work_id: str, source_kind: str, verified: bool, confidence: float) -> dict[str, Any]:
    item = dict(raw) if isinstance(raw, dict) else {"symptom": _text(raw)}
    return {"task_family": _text(item.get("task_family") or task_family), "component": _text(item.get("component")), "subsystem": _text(item.get("subsystem")), "failure_signature": _text(item.get("failure_signature")), "invariant": _text(item.get("invariant")), "symptom": _text(item.get("symptom") or item.get("finding") or item.get("description")), "reproduction": _text(item.get("reproduction")), "fix": _text(item.get("fix")), "test_pointer": _text(item.get("test_pointer")), "evidence_pointer": _text(item.get("evidence_pointer") or work_id), "severity": _text(item.get("severity") or "medium"), "confidence": float(item.get("confidence", confidence) or 0.0), "source_kind": _text(item.get("source_kind") or source_kind), "source_ref": _text(item.get("source_ref") or work_id), "verified": bool(verified)}

def integrate_work_report(root: Path, *, report: WorkReport, manifest: dict[str, Any] | None = None, jira_id: str = "", work_type: str = "", requirements: Any = None, replay_results: Any = None) -> dict[str, Any]:
    """Persist report traceability; requirement links are evidence-only and never fabricated."""
    root = Path(root); manifest = manifest if isinstance(manifest, dict) else {}
    task_family = _text(work_type or report.status or "engineering-work")
    validation = manifest.get("validation", {}) if isinstance(manifest.get("validation"), dict) else {}
    verification = bool(validation.get("passed")); completed = report.status == "completed" and verification
    findings = _items(manifest.get("findings")) + list(report.findings); regressions = _items(manifest.get("regressions")) + list(report.regressions)
    controller = LearningController(root); knowledge_ids: list[str] = []; pending_ids: list[str] = []
    for raw in findings + regressions:
        item = _knowledge_item(raw, task_family=task_family, work_id=report.work_id, source_kind="work-report", verified=completed, confidence=1.0 if completed else 0.0)
        if not item["symptom"]: continue
        kid = controller.record_regression(task_family=item["task_family"], component=item["component"], subsystem=item["subsystem"], failure_signature=item["failure_signature"], invariant=item["invariant"], symptom=item["symptom"], reproduction=item["reproduction"], fix=item["fix"], test_pointer=item["test_pointer"], evidence_pointer=item["evidence_pointer"], severity=item["severity"], confidence=item["confidence"], source_kind=item["source_kind"], source_ref=item["source_ref"], verified=item["verified"])
        (knowledge_ids if item["verified"] and item["test_pointer"] else pending_ids).append(kid)
    historical = controller.regression_memory.retrieve(task_family=task_family, limit=25)
    historical_ids = [k.knowledge_id for k in historical if k.knowledge_id not in knowledge_ids]

    requirement_source = dict(requirements) if isinstance(requirements, dict) else dict(manifest)
    if jira_id: requirement_source["jira_id"] = jira_id
    normalized = normalize_requirements(requirement_source, fallback_goal=_text(report.objective))
    replay = _items(replay_results) if replay_results is not None else _items(manifest.get("replay_results"))
    requirement_payload = persist_requirement_traceability(root, report.work_id, jira_id=jira_id, work_type=work_type, requirements=normalized, regression_ids=knowledge_ids + historical_ids, replay=replay, evidence=report.evidence, source=f".ai-harness/reports/{report.work_id}.html")

    trace = {"traceability_version": TRACEABILITY_VERSION, "work_id": report.work_id, "jira_id": jira_id, "work_type": work_type, "task_family": task_family, "generated_at": int(time.time()), "verification_passed": verification, "work_completed": completed, "new_verified_regression_ids": sorted(set(knowledge_ids)), "new_pending_regression_ids": sorted(set(pending_ids)), "historical_regression_ids": sorted(set(historical_ids)), "requirement_traceability": {"schema_version": requirement_payload["schema_version"], "path": f".ai-harness/reports/traceability/{report.work_id}-requirements.json", "coverage": requirement_payload["coverage"]}, "planning_inputs": {"historical_regressions": sorted(set(historical_ids)), "requirement_ids": sorted({x["requirement_id"] for x in requirement_payload["requirements"]}), "require_replay": bool(historical_ids or knowledge_ids or replay), "source": "RegressionMemory + requirement traceability"}, "provenance": {"report": f".ai-harness/reports/{report.work_id}.html", "memory": ".ai-harness/learning/regression-memory.db", "requirements": f".ai-harness/reports/traceability/{report.work_id}-requirements.json"}}
    trace_dir = root / ".ai-harness" / "reports" / "traceability"; trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{report.work_id}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ".ai-harness" / "reports" / "planning-context.json").write_text(json.dumps(trace["planning_inputs"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _append_html_traceability(root, report, trace, requirement_payload)
    return trace

def _append_html_traceability(root: Path, report: WorkReport, trace: dict[str, Any], requirement_payload: dict[str, Any]) -> None:
    path = root / ".ai-harness" / "reports" / (report.work_id + ".html")
    if not path.is_file(): return
    html = path.read_text(encoding="utf-8"); marker = "<!-- work-report-traceability -->"
    if marker in html: return
    coverage = requirement_payload["coverage"]; rows = []
    keys = ("requirement_id", "criterion_id", "status", "design_pointer", "code_pointer", "test_pointer", "evidence_pointer", "replay_status", "residual_gap")
    for item in requirement_payload["requirements"]:
        rows.append("<tr>" + "".join("<td>" + escape(str(item.get(key, ""))) + "</td>" for key in keys) + "</tr>")
    headers = ("Requirement", "Criterion", "Status", "Design", "Code", "Test", "Evidence", "Replay", "Residual gap")
    table = "<table><thead><tr>" + "".join(f"<th>{escape(x)}</th>" for x in headers) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    section = marker + "<section><h2>Requirement-level traceability</h2><p><b>Chain:</b> Jira/Requirement → Acceptance Criterion → Design → Code change → Test → Evidence → Regression → Replay result → WorkReport</p>" + f"<p><b>Coverage:</b> {coverage['covered']} covered · {coverage['partial']} partial · {coverage['uncovered']} uncovered</p>" + (table if rows else "<p class=muted>No explicit requirements or acceptance criteria were supplied.</p>") + "<p><b>Rule:</b> missing evidence remains a gap; historical regressions are advisory and replay, shadow, canary, promotion and rollback gates remain authoritative.</p></section>" + "<section><h2>Learning and regression traceability</h2>" + f"<p><b>Traceability version:</b> {escape(trace['traceability_version'])} · <b>Verification passed:</b> {escape(str(trace['verification_passed']))}</p><p><b>Historical regressions:</b> {len(trace['historical_regression_ids'])} · <b>New verified:</b> {len(trace['new_verified_regression_ids'])} · <b>Pending:</b> {len(trace['new_pending_regression_ids'])}</p>" + ("<ul>" + "".join(f"<li>{escape(x)}</li>" for x in trace["historical_regression_ids"]) + "</ul>" if trace["historical_regression_ids"] else "<p class=muted>None.</p>") + "</section>"
    path.write_text(html.replace("</main>", section + "</main>"), encoding="utf-8")
    latest = root / ".ai-harness" / "reports" / "latest.html"
    if latest.is_file() and marker not in latest.read_text(encoding="utf-8"):
        latest.write_text(latest.read_text(encoding="utf-8").replace("</main>", section + "</main>"), encoding="utf-8")
