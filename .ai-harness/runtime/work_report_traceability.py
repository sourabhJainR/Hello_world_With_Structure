#!/usr/bin/env python3
"""Bridge engineering reports, verified regression knowledge, planning context and replay provenance."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json
import time

try:
    from .learning_controller import LearningController
    from .work_report import WorkReport, WorkReportGenerator
except ImportError:
    from learning_controller import LearningController
    from work_report import WorkReport, WorkReportGenerator


TRACEABILITY_VERSION = "1.0"


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _knowledge_item(raw: Any, *, task_family: str, work_id: str, source_kind: str, verified: bool, confidence: float) -> dict[str, Any]:
    if isinstance(raw, dict):
        item = dict(raw)
    else:
        item = {"symptom": _text(raw)}
    return {
        "task_family": _text(item.get("task_family") or task_family),
        "component": _text(item.get("component")),
        "subsystem": _text(item.get("subsystem")),
        "failure_signature": _text(item.get("failure_signature")),
        "invariant": _text(item.get("invariant")),
        "symptom": _text(item.get("symptom") or item.get("finding") or item.get("description")),
        "reproduction": _text(item.get("reproduction")),
        "fix": _text(item.get("fix")),
        "test_pointer": _text(item.get("test_pointer")),
        "evidence_pointer": _text(item.get("evidence_pointer") or work_id),
        "severity": _text(item.get("severity") or "medium"),
        "confidence": float(item.get("confidence", confidence) or 0.0),
        "source_kind": _text(item.get("source_kind") or source_kind),
        "source_ref": _text(item.get("source_ref") or work_id),
        "verified": bool(verified),
    }


def integrate_work_report(root: Path, *, report: WorkReport, manifest: dict[str, Any] | None = None,
                          jira_id: str = "", work_type: str = "") -> dict[str, Any]:
    """Persist report traceability and promote only explicitly verified findings into regression memory.

    This function is deliberately conservative: it never infers a defect, root cause, test, or fix.
    A finding becomes active regression knowledge only when the work completed successfully, verification
    passed, and the finding supplies both evidence and a test pointer (enforced by RegressionMemory).
    """
    root = Path(root)
    manifest = manifest if isinstance(manifest, dict) else {}
    task_family = _text(work_type or report.status or "engineering-work")
    verification = bool(manifest.get("validation", {}).get("passed")) if isinstance(manifest.get("validation"), dict) else False
    completed = report.status == "completed" and verification
    findings = _items(manifest.get("findings")) + list(report.findings)
    regressions = _items(manifest.get("regressions")) + list(report.regressions)
    controller = LearningController(root)
    knowledge_ids: list[str] = []
    pending_ids: list[str] = []

    for raw in findings + regressions:
        item = _knowledge_item(raw, task_family=task_family, work_id=report.work_id,
                               source_kind="work-report", verified=completed, confidence=1.0 if completed else 0.0)
        if not item["symptom"]:
            continue
        kid = controller.record_regression(
            task_family=item["task_family"], component=item["component"], subsystem=item["subsystem"],
            failure_signature=item["failure_signature"], invariant=item["invariant"], symptom=item["symptom"],
            reproduction=item["reproduction"], fix=item["fix"], test_pointer=item["test_pointer"],
            evidence_pointer=item["evidence_pointer"], severity=item["severity"], confidence=item["confidence"],
            source_kind=item["source_kind"], source_ref=item["source_ref"], verified=item["verified"],
        )
        (knowledge_ids if item["verified"] and item["test_pointer"] else pending_ids).append(kid)

    historical = controller.regression_memory.retrieve(task_family=task_family, limit=25)
    historical_ids = [k.knowledge_id for k in historical if k.knowledge_id not in knowledge_ids]

    trace = {
        "traceability_version": TRACEABILITY_VERSION,
        "work_id": report.work_id,
        "jira_id": jira_id,
        "work_type": work_type,
        "task_family": task_family,
        "generated_at": int(time.time()),
        "verification_passed": verification,
        "work_completed": completed,
        "new_verified_regression_ids": sorted(set(knowledge_ids)),
        "new_pending_regression_ids": sorted(set(pending_ids)),
        "historical_regression_ids": sorted(set(historical_ids)),
        "planning_inputs": {
            "historical_regressions": sorted(set(historical_ids)),
            "require_replay": bool(historical_ids or knowledge_ids),
            "source": "RegressionMemory",
        },
        "provenance": {
            "report": str((root / ".ai-harness" / "reports" / (report.work_id + ".html")).relative_to(root)),
            "memory": str((root / ".ai-harness" / "learning" / "regression-memory.db").relative_to(root)),
        },
    }
    trace_dir = root / ".ai-harness" / "reports" / "traceability"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / f"{report.work_id}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ".ai-harness" / "reports" / "planning-context.json").write_text(json.dumps(trace["planning_inputs"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _append_html_traceability(root, report, trace)
    return trace


def _append_html_traceability(root: Path, report: WorkReport, trace: dict[str, Any]) -> None:
    path = root / ".ai-harness" / "reports" / (report.work_id + ".html")
    if not path.is_file():
        return
    html = path.read_text(encoding="utf-8")
    marker = "<!-- work-report-traceability -->"
    if marker in html:
        return
    section = (
        marker + "<section><h2>Learning and regression traceability</h2>"
        f"<p><b>Traceability version:</b> {trace['traceability_version']} · "
        f"<b>Verification passed:</b> {trace['verification_passed']}</p>"
        f"<p><b>Historical regressions used as planning inputs:</b> {len(trace['historical_regression_ids'])}</p>"
        f"<p><b>New verified regression knowledge:</b> {len(trace['new_verified_regression_ids'])}</p>"
        f"<p><b>Pending knowledge:</b> {len(trace['new_pending_regression_ids'])}</p>"
        "<h3>Historical regression IDs</h3>"
        + ("<ul>" + "".join(f"<li>{x}</li>" for x in trace["historical_regression_ids"]) + "</ul>" if trace["historical_regression_ids"] else "<p class=muted>None.</p>")
        + "<h3>New verified regression IDs</h3>"
        + ("<ul>" + "".join(f"<li>{x}</li>" for x in trace["new_verified_regression_ids"]) + "</ul>" if trace["new_verified_regression_ids"] else "<p class=muted>None.</p>")
        + "<p><b>Planning rule:</b> historical knowledge is advisory input only; replay, shadow, canary and promotion gates remain authoritative.</p></section>"
    )
    path.write_text(html.replace("</main>", section + "</main>"), encoding="utf-8")
    latest = root / ".ai-harness" / "reports" / "latest.html"
    if latest.is_file():
        latest.write_text(latest.read_text(encoding="utf-8").replace("</main>", section + "</main>"), encoding="utf-8")
