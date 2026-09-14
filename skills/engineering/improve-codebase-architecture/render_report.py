#!/usr/bin/env python3
"""Render structured architecture candidates into a self-contained HTML report.

Input JSON shape:
{
  "repository": "name",
  "generated_at": "ISO timestamp",
  "candidates": [
    {
      "id": "candidate-id",
      "title": "Deepen ...",
      "strength": "Strong|Worth exploring|Speculative",
      "dependency": "in-process|local-substitutable|ports-and-adapters|mock",
      "files": ["path.py::Symbol"],
      "problem": "...",
      "solution": "...",
      "wins": ["..."],
      "before_mermaid": "flowchart LR ...",
      "after_mermaid": "flowchart LR ...",
      "adr": "optional"
    }
  ],
  "top_recommendation": "candidate-id"
}
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def esc(value: object) -> str:
    return html.escape(str(value))


def render(data: dict) -> str:
    repo = esc(data.get("repository", "repository"))
    generated = esc(data.get("generated_at", ""))
    candidates = data.get("candidates", [])
    top_id = data.get("top_recommendation", "")

    cards: list[str] = []
    anchors: dict[str, str] = {}
    for index, candidate in enumerate(candidates, 1):
        cid = str(candidate.get("id", f"candidate-{index}"))
        anchor = "candidate-" + "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in cid).strip("-")
        anchors[cid] = anchor
        strength = str(candidate.get("strength", "Worth exploring"))
        badge_class = {"Strong": "strong", "Worth exploring": "worth", "Speculative": "spec"}.get(strength, "spec")
        files = "".join(f'<li><code>{esc(item)}</code></li>' for item in candidate.get("files", []))
        wins = "".join(f'<li>{esc(item)}</li>' for item in candidate.get("wins", []))
        adr = candidate.get("adr", "")
        adr_html = f'<div class="adr"><strong>ADR:</strong> {esc(adr)}</div>' if adr else ""
        before = str(candidate.get("before_mermaid", "")).strip() or "flowchart LR\nA[No before diagram supplied]"
        after = str(candidate.get("after_mermaid", "")).strip() or "flowchart LR\nA[No after diagram supplied]"
        cards.append(f'''
<article id="{esc(anchor)}" class="card">
  <div class="row title-row"><h2>{esc(candidate.get("title", cid))}</h2><div><span class="badge {badge_class}">{esc(strength)}</span><span class="badge dep">{esc(candidate.get("dependency", "in-process"))}</span></div></div>
  <div class="meta"><strong>Files</strong><ul>{files}</ul></div>
  <div class="diagrams">
    <section><div class="diagram-label">BEFORE</div><div class="diagram"><pre class="mermaid">{esc(before)}</pre></div></section>
    <section><div class="diagram-label">AFTER</div><div class="diagram"><pre class="mermaid">{esc(after)}</pre></div></section>
  </div>
  <div class="copy"><p><strong>Problem:</strong> {esc(candidate.get("problem", ""))}</p><p><strong>Solution:</strong> {esc(candidate.get("solution", ""))}</p></div>
  <div class="wins"><strong>Wins</strong><ul>{wins}</ul></div>
  {adr_html}
</article>''')

    top = next((c for c in candidates if str(c.get("id", "")) == str(top_id)), None)
    top_html = ""
    if top:
        top_anchor = anchors.get(str(top_id), "")
        top_html = f'<section class="top"><h2>Top recommendation</h2><p><a href="#{esc(top_anchor)}">{esc(top.get("title", top_id))}</a>: {esc(top.get("solution", ""))}</p></section>'

    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Architecture review for {repo}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"; mermaid.initialize({{startOnLoad:true,theme:"neutral",securityLevel:"loose"}});</script>
<style>
body{{margin:0;background:#fafaf9;color:#0f172a;font-family:ui-sans-serif,system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:44px 24px 80px}}.header{{margin-bottom:36px}}h1{{font-size:34px;margin:0 0 8px}}h2{{font-size:22px;margin:0}}.muted{{color:#64748b;font-size:13px}}.card,.top{{background:white;border:1px solid #e2e8f0;border-radius:14px;padding:24px;margin:0 0 28px;box-shadow:0 3px 14px rgba(15,23,42,.04)}}.row{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}}.badge{{display:inline-block;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:700;margin-left:6px}}.strong{{background:#d1fae5;color:#065f46}}.worth{{background:#fef3c7;color:#92400e}}.spec{{background:#e2e8f0;color:#475569}}.dep{{background:#eef2ff;color:#3730a3}}.meta{{margin:18px 0}}ul{{margin:8px 0 0;padding-left:18px}}code{{font-family:ui-monospace,monospace;font-size:12px}}.diagrams{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:22px 0}}.diagram-label{{font-size:10px;letter-spacing:.14em;font-weight:800;color:#64748b;margin-bottom:6px}}.diagram{{height:330px;border:1px dashed #cbd5e1;border-radius:10px;padding:10px;overflow:auto;background:#f8fafc}}.copy p{{margin:10px 0;line-height:1.55}}.wins ul{{display:flex;flex-wrap:wrap;gap:7px;list-style:none;padding:0}}.wins li{{background:#f1f5f9;border-radius:8px;padding:6px 9px;font-size:12px}}.adr{{margin-top:16px;padding:10px 12px;border-left:4px solid #f59e0b;background:#fffbeb}}a{{color:#334155;font-weight:700;text-decoration:underline}}@media(max-width:800px){{.diagrams{{grid-template-columns:1fr}}}}
</style></head>
<body><main>
<header class="header"><div class="muted">ARCHITECTURE REVIEW · {generated}</div><h1>{repo}</h1><div class="muted">solid box = module · dashed line = seam · red edge = leakage · dark box = deep module</div></header>
<section id="candidates">{''.join(cards)}</section>
{top_html}
</main></body></html>'''


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: render_report.py INPUT.json [OUTPUT.html]", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    data = json.loads(source.read_text(encoding="utf-8"))
    output = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("/tmp") / f"architecture-review-{int(source.stat().st_mtime)}.html"
    output.write_text(render(data), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
