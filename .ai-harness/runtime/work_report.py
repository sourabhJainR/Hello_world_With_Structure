#!/usr/bin/env python3
"""Generate self-contained HTML engineering reports for every orchestrated work item."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import escape
from pathlib import Path
from typing import Any, Iterable
import json
import re
import time


@dataclass
class WorkReport:
    """Structured evidence contract rendered to HTML without external dependencies."""

    work_id: str
    title: str
    status: str = "in-progress"
    objective: str = ""
    summary: str = ""
    started_at: str = ""
    completed_at: str = ""
    scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    implementation: list[str] = field(default_factory=list)
    hld: list[str] = field(default_factory=list)
    lld: list[str] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    data_flow: list[str] = field(default_factory=list)
    user_flow: list[str] = field(default_factory=list)
    uml: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class WorkReportGenerator:
    """Render and persist a complete, navigable engineering report."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.report_dir = self.root / ".ai-harness" / "reports"

    def write(self, report: WorkReport) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        filename = _safe_name(report.work_id) + ".html"
        path = self.report_dir / filename
        path.write_text(self.render(report), encoding="utf-8")
        (self.report_dir / "latest.html").write_text(self.render(report), encoding="utf-8")
        return path

    def render(self, report: WorkReport) -> str:
        sections = []
        sections.append(_section("Executive summary", [report.summary or report.objective], report.objective))
        sections.append(_cards(report))
        sections.append(_section("Scope, assumptions and boundaries", _merge(report.scope, report.out_of_scope, report.assumptions, report.constraints)))
        sections.append(_section("Findings and decisions", _merge(report.findings, report.decisions)))
        sections.append(_section("HLD", report.hld))
        sections.append(_section("LLD / implementation", report.lld + report.implementation))
        sections.append(_diagram_section("System / component flow", _flow_mermaid(report)))
        sections.append(_diagram_section("Data flow", _data_mermaid(report)))
        sections.append(_diagram_section("User / use-case flow", _user_mermaid(report)))
        sections.append(_diagram_section("UML sequence", _uml_mermaid(report)))
        sections.append(_section("Verification and regression areas", _merge(report.verification, report.regressions)))
        sections.append(_section("Risks and threats", _merge(report.risks, report.threats)))
        sections.append(_table_section("Evidence and references", report.references or report.evidence))
        sections.append(_section("Open questions", report.open_questions))
        sections.append(_section("Event / audit trail", [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in report.events]))
        sections.append(_metrics(report.metrics))
        return _html_shell(report, "".join(sections))


def report_from_observation(*, work_id: str, task_class: str, strategy: str, observation: Any,
                            events: Iterable[dict[str, Any]] = (), references: Iterable[dict[str, Any]] = (),
                            assumptions: Iterable[str] = (), boundaries: Iterable[str] = (),
                            risks: Iterable[str] = (), threats: Iterable[str] = (),
                            findings: Iterable[str] = (), regressions: Iterable[str] = ()) -> WorkReport:
    success = bool(getattr(observation, "success", False))
    verification = bool(getattr(observation, "verification_passed", False))
    return WorkReport(
        work_id=str(work_id), title=f"Engineering work: {task_class}", status="completed" if success else "failed",
        objective=f"Execute and verify task family '{task_class}' using strategy '{strategy}'.",
        summary=("Work completed and recorded with evidence." if success else "Work did not complete successfully; preserve evidence and investigate."),
        scope=[f"task_class={task_class}", f"strategy={strategy}"], out_of_scope=["Unrequested security or permission changes"],
        assumptions=list(assumptions), constraints=list(boundaries), findings=list(findings), risks=list(risks), threats=list(threats),
        regressions=list(regressions), implementation=[f"success={success}", f"accepted={getattr(observation, 'accepted', False)}"],
        hld=["Intent -> repository evidence -> capability execution -> verification -> evidence -> learning."],
        lld=["Experience is persisted before candidate evaluation; promotion remains gated by replay, shadow and canary."],
        references=list(references), evidence=[{"type": "observation", "id": str(getattr(observation, 'task_id', work_id)), "policy_id": getattr(observation, 'policy_id', '')}],
        decisions=[f"verification_passed={verification}", f"safety_passed={getattr(observation, 'safety_passed', True)}"],
        verification=["Verification status is captured as a durable observation."],
        data_flow=["User task", "Repository/context evidence", "Agent/tool execution", "Verification", "Experience store", "Learning gates"],
        user_flow=["Request work", "Inspect evidence", "Execute", "Review result", "Verify", "Receive report"],
        uml=["actor User", "participant Orchestrator", "participant Agent", "participant Verifier", "database ExperienceStore", "User->Orchestrator: task", "Orchestrator->Agent: bounded work", "Agent->Verifier: result", "Verifier->ExperienceStore: evidence", "Orchestrator->User: HTML report"],
        events=list(events), metrics={"retries": getattr(observation, "retries", 0), "regressions": getattr(observation, "regressions", 0), "cost": getattr(observation, "cost", 0), "latency_ms": getattr(observation, "latency_ms", 0)},
    )


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-")
    return cleaned[:120] or "work"


def _merge(*groups: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(x) for group in groups for x in group if str(x).strip()))


def _section(title: str, items: Iterable[str], lead: str = "") -> str:
    rows = "".join(f"<li>{escape(str(x))}</li>" for x in items if str(x).strip())
    return f"<section><h2>{escape(title)}</h2>{f'<p>{escape(lead)}</p>' if lead else ''}{'<ul>'+rows+'</ul>' if rows else '<p class=muted>No evidence recorded.</p>'}</section>"


def _cards(r: WorkReport) -> str:
    cards = [("Status", r.status), ("Work ID", r.work_id), ("Generated", r.generated_at), ("Evidence", str(len(r.evidence))), ("References", str(len(r.references))), ("Risks", str(len(r.risks)+len(r.threats)))]
    return "<div class=cards>" + "".join(f"<div class=card><b>{escape(k)}</b><span>{escape(str(v))}</span></div>" for k,v in cards) + "</div>"


def _diagram_section(title: str, diagram: str) -> str:
    return f"<section><h2>{escape(title)}</h2><div class=diagram><div class=mermaid>{escape(diagram)}</div><details><summary>Diagram source</summary><pre>{escape(diagram)}</pre></details></div></section>"


def _flow_mermaid(r: WorkReport) -> str:
    return "flowchart LR\nA[User task] --> B[Intent & contract]\nB --> C[Repository evidence]\nC --> D[Capability / dependency graph]\nD --> E[Agent execution]\nE --> F[Verification & review]\nF --> G[Evidence / report]\nG --> H[Learning gates]\nH --> I[Active policy or rollback]"


def _data_mermaid(r: WorkReport) -> str:
    return "flowchart TD\nU[Task input] --> X[Context + repository facts]\nX --> A[Execution observations]\nA --> V[Verification results]\nV --> S[(Experience Store)]\nS --> L[Candidate scoring]\nL --> R[Regression replay]\nR --> C[Shadow / Canary]\nC --> P[Policy Registry]"


def _user_mermaid(r: WorkReport) -> str:
    return "flowchart LR\nU((User)) --> Q[Request]\nQ --> I[Inspect evidence]\nI --> W[Work]\nW --> V[Verify]\nV --> H[HTML engineering report]\nH --> U"


def _uml_mermaid(r: WorkReport) -> str:
    lines = ["sequenceDiagram", "actor User", "participant O as Orchestrator", "participant A as Agent", "participant V as Verifier", "participant S as Experience Store"]
    lines += ["User->>O: submit work", "O->>A: bounded execution", "A-->>O: observations", "O->>V: verify result", "V-->>O: evidence", "O->>S: persist experience", "O-->>User: HTML report"]
    return "\n".join(lines)


def _table_section(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return _section(title, [])
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in (row.values() if isinstance(row, dict) else [row])) + "</tr>" for row in rows)
    return f"<section><h2>{escape(title)}</h2><div class=tablewrap><table><tbody>{body}</tbody></table></div></section>"


def _metrics(metrics: dict[str, Any]) -> str:
    return _section("Metrics", [f"{k}: {v}" for k,v in metrics.items()])


def _html_shell(r: WorkReport, body: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(r.title)}</title><style>
:root{{font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:#172033;background:#f5f7fb}}body{{margin:0}}header{{padding:28px 6vw;background:#172033;color:white}}main{{max-width:1200px;margin:auto;padding:24px}}section{{background:white;border:1px solid #dfe4ec;border-radius:12px;padding:20px;margin:16px 0;box-shadow:0 2px 8px #0000000a}}h1{{margin:0 0 8px}}h2{{margin-top:0}}.muted{{color:#667085}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}}.card{{background:white;border:1px solid #dfe4ec;border-radius:10px;padding:14px}}.card span{{display:block;margin-top:6px;font-size:1.05rem}}li{{margin:6px 0}}pre{{white-space:pre-wrap;overflow:auto;background:#111827;color:#e5e7eb;padding:14px;border-radius:8px}}.diagram{{overflow:auto}}table{{border-collapse:collapse;width:100%}}td{{border:1px solid #dfe4ec;padding:8px;vertical-align:top}}details{{margin-top:12px}}@media print{{section{{break-inside:avoid;box-shadow:none}}header{{color:#000;background:white}}}}
</style></head><body><header><h1>{escape(r.title)}</h1><div>{escape(r.work_id)} · {escape(r.status)}</div><div>{escape(r.generated_at)}</div></header><main>{body}<footer><p class=muted>Generated by the engineering work-report subsystem. Report is evidence, not approval. Unknowns remain explicitly marked.</p></footer></main></body></html>'''
