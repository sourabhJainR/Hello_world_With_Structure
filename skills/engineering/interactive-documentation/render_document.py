#!/usr/bin/env python3
"""Render a typed repository-backed visual document as one self-contained HTML file."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def validate(data: dict) -> None:
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    ids = [str(n.get("id", "")) for n in nodes]
    if not ids or any(not x for x in ids):
        raise ValueError("nodes must contain non-empty ids")
    if len(ids) != len(set(ids)):
        raise ValueError("node ids must be unique")
    known = set(ids)
    for edge in edges:
        if str(edge.get("source")) not in known or str(edge.get("target")) not in known:
            raise ValueError("every edge source/target must reference a node")
    for view in data.get("views", []):
        for node_id in view.get("nodes", []):
            if str(node_id) not in known:
                raise ValueError("view references an unknown node")


def render(data: dict) -> str:
    validate(data)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    title = esc(data.get("title", "Interactive system documentation"))
    repo = esc(data.get("repository", "repository"))
    digest = esc(data.get("snapshot_digest", "unknown"))
    generated = esc(data.get("generated_at", ""))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f8fafc;--panel:#fff;--text:#0f172a;--muted:#64748b;--line:#cbd5e1;--accent:#2563eb;--node:#eef2ff;--node-border:#818cf8;--edge:#64748b;--danger:#b91c1c;--shadow:0 8px 28px rgba(15,23,42,.08)}}
:root.dark{{--bg:#0b1120;--panel:#111827;--text:#e5e7eb;--muted:#94a3b8;--line:#334155;--accent:#60a5fa;--node:#172554;--node-border:#6366f1;--edge:#94a3b8;--danger:#f87171;--shadow:0 10px 32px rgba(0,0,0,.28)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}button,input{{font:inherit}}button{{cursor:pointer}}header{{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--panel) 94%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:12px 18px}}.bar{{display:flex;gap:12px;align-items:center;max-width:1500px;margin:auto}}.title{{font-weight:800;font-size:17px;flex:1}}.muted{{color:var(--muted);font-size:12px}}button,.search{{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:9px;padding:7px 10px}}.search{{width:220px;outline:none}}main{{max-width:1500px;margin:auto;padding:18px;display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px}}.toolbar{{grid-column:1/-1;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}.canvas{{position:relative;min-height:680px;background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}}svg{{width:100%;height:680px;display:block;background:radial-gradient(circle at 20% 20%,color-mix(in srgb,var(--accent) 5%,transparent),transparent 30%)}}.node rect{{fill:var(--node);stroke:var(--node-border);stroke-width:2;rx:12}}.node text{{fill:var(--text);font-size:13px;font-weight:700;pointer-events:none}}.node .kind{{font-size:10px;font-weight:600;fill:var(--muted)}}.edge{{stroke:var(--edge);stroke-width:2;fill:none;marker-end:url(#arrow)}}.edge.active{{stroke:var(--accent);stroke-width:3}}.node.active rect{{stroke:var(--accent);stroke-width:3}}.node.dim,.edge.dim{{opacity:.18}}aside{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:var(--shadow);min-height:680px;overflow:auto}}h1,h2,h3{{margin:0 0 8px}}h1{{font-size:26px}}h2{{font-size:17px}}h3{{font-size:13px;margin-top:18px}}ul{{padding-left:18px}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}}.status{{padding:8px 10px;border-radius:9px;background:color-mix(in srgb,var(--accent) 10%,transparent);margin:10px 0}}.warning{{color:var(--danger)}}.views button{{margin:3px 3px 0 0}}.hint{{position:absolute;left:12px;bottom:12px;padding:7px 9px;background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:11px}}@media(max-width:1000px){{main{{grid-template-columns:1fr}}aside{{min-height:0}}}}@media print{{header,.toolbar,.hint,aside{{display:none}}main{{display:block;padding:0}}.canvas{{border:0;box-shadow:none}}svg{{height:900px}}}}
</style></head><body>
<header><div class="bar"><div class="title">{title}<div class="muted">{repo} · snapshot {digest} · {generated}</div></div><input id="search" class="search" aria-label="Search nodes" placeholder="Find node…"><button id="theme" title="Toggle theme">Theme</button><button id="reset" title="Reset view">Reset</button><button id="print">Print</button></div></header>
<main><div class="toolbar"><div id="views" class="views"></div><span class="muted">Click a node for details. Trace authored upstream/downstream relationships from the details panel.</span></div>
<section class="canvas" aria-label="Interactive system map"><svg id="map" viewBox="0 0 1200 680" role="img" aria-label="Interactive architecture diagram"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="var(--edge)"></path></marker></defs><g id="edges"></g><g id="nodes"></g></svg><div class="hint">/ search · Esc clear · click node · keyboard Tab to navigate</div></section>
<aside id="details"><h2>Documentation</h2><p class="muted">Select a node to inspect its role, authored relationships, source references, and evidence.</p><div class="status"><strong>Evidence</strong><br>Snapshot: <code>{digest}</code></div></aside></main>
<script>
const DATA={payload};
const NS='http://www.w3.org/2000/svg';
const nodes=DATA.nodes||[], edges=DATA.edges||[]; const byId=new Map(nodes.map(n=>[String(n.id),n]));
const edgeLayer=document.getElementById('edges'), nodeLayer=document.getElementById('nodes'), details=document.getElementById('details');
let selected=null, activeView=null;
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function positions(){{const cols=Math.max(1,Math.ceil(Math.sqrt(nodes.length))); const gapX=270,gapY=145; return new Map(nodes.map((n,i)=>[String(n.id),{{x:90+(i%cols)*gapX,y:80+Math.floor(i/cols)*gapY}}]))}}
const pos=positions();
function draw(){{edgeLayer.innerHTML='';nodeLayer.innerHTML=''; const visible=activeView?new Set(activeView.nodes||[]):null;
 for(const e of edges){{const a=pos.get(String(e.source)),b=pos.get(String(e.target));if(!a||!b)continue;const line=document.createElementNS(NS,'path');line.setAttribute('d',`M ${{a.x+150}} ${{a.y+35}} C ${{a.x+210}} ${{a.y+35}}, ${{b.x-60}} ${{b.y+35}}, ${{b.x}} ${{b.y+35}}`);line.classList.add('edge');line.dataset.source=e.source;line.dataset.target=e.target;line.setAttribute('aria-label',`${{e.source}} to ${{e.target}}: ${{e.label||e.type||'relationship'}}`);if(visible&&(!visible.has(String(e.source))||!visible.has(String(e.target))))line.classList.add('dim');edgeLayer.appendChild(line)}}
 for(const n of nodes){{const id=String(n.id),p=pos.get(id),g=document.createElementNS(NS,'g');g.classList.add('node');g.setAttribute('tabindex','0');g.dataset.id=id;g.setAttribute('role','button');g.setAttribute('aria-label',`${{n.label||id}} ${{n.kind||'component'}}`);if(visible&&!visible.has(id))g.classList.add('dim');const r=document.createElementNS(NS,'rect');r.setAttribute('x',p.x);r.setAttribute('y',p.y);r.setAttribute('width',150);r.setAttribute('height',70);g.appendChild(r);const t=document.createElementNS(NS,'text');t.setAttribute('x',p.x+12);t.setAttribute('y',p.y+28);t.textContent=n.label||id;g.appendChild(t);const k=document.createElementNS(NS,'text');k.setAttribute('x',p.x+12);k.setAttribute('y',p.y+49);k.classList.add('kind');k.textContent=n.kind||'component';g.appendChild(k);g.onclick=()=>select(id);g.onkeydown=e=>{{if(e.key==='Enter'||e.key===' '){{e.preventDefault();select(id)}}}};nodeLayer.appendChild(g)}};if(selected){{focusVisual(selected)}}}}
function select(id){{selected=String(id);const n=byId.get(selected);if(!n)return;const related=edges.filter(e=>String(e.source)===selected||String(e.target)===selected);details.innerHTML=`<h2>${{esc(n.label||selected)}}</h2><div class="muted">${{esc(n.kind||'component')}}</div><p>${{esc(n.description||'')}}</p><h3>Role</h3><p>${{esc(n.role||'')}}</p><h3>Relationships</h3><ul>${{related.map(e=>`<li><button data-trace="${{esc(e.source)}}:${{esc(e.target)}}">${{esc(e.label||e.type||'relationship')}}: ${{esc(e.source)}} → ${{esc(e.target)}}</button></li>`).join('')||'<li>None authored</li>'}}</ul><h3>Source</h3><ul>${{(n.sources||[]).map(s=>`<li><code>${{esc(s)}}</code></li>`).join('')||'<li>Not supplied</li>'}}</ul><h3>Evidence</h3><ul>${{(n.evidence_ids||[]).map(s=>`<li><code>${{esc(s)}}</code></li>`).join('')||'<li>Not supplied</li>'}}</ul>${{n.unknowns?.length?`<h3 class="warning">Unknowns</h3><ul>${{n.unknowns.map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul>`:''}}`;details.querySelectorAll('[data-trace]').forEach(b=>b.onclick=()=>{{const [a,c]=b.dataset.trace.split(':');trace(a,c)}});focusVisual(selected)}}
function focusVisual(id){{document.querySelectorAll('.node').forEach(g=>g.classList.toggle('active',g.dataset.id===id));const linked=new Set(edges.filter(e=>String(e.source)===id||String(e.target)===id).flatMap(e=>[String(e.source),String(e.target)]));document.querySelectorAll('.node,.edge').forEach(el=>el.classList.toggle('dim',el.classList.contains('node')&&!linked.has(el.dataset.id)&&el.dataset.id!==id));document.querySelectorAll('.edge').forEach(el=>el.classList.toggle('active',el.dataset.source===id||el.dataset.target===id))}}
function trace(a,b){{selected=a;document.querySelectorAll('.edge').forEach(e=>e.classList.toggle('active',e.dataset.source===a&&e.dataset.target===b));select(a)}}
function renderViews(){{const root=document.getElementById('views');root.innerHTML='';(DATA.views||[]).forEach(v=>{{const b=document.createElement('button');b.textContent=v.label||v.id;b.onclick=()=>{{activeView=v;draw()}};root.appendChild(b)}});}}
function reset(){{selected=null;activeView=null;details.innerHTML='<h2>Documentation</h2><p class="muted">Select a node to inspect its role, authored relationships, source references, and evidence.</p>';draw()}}
document.getElementById('search').oninput=e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('.node').forEach(g=>g.classList.toggle('dim',q&&!g.textContent.toLowerCase().includes(q)))}};
document.getElementById('theme').onclick=()=>document.documentElement.classList.toggle('dark');document.getElementById('reset').onclick=reset;document.getElementById('print').onclick=()=>window.print();document.addEventListener('keydown',e=>{{if(e.key==='/'&&document.activeElement.tagName!=='INPUT'){{e.preventDefault();document.getElementById('search').focus()}}if(e.key==='Escape'){{document.getElementById('search').value='';reset()}}}});
renderViews();draw();
</script></body></html>'''


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_document.py INPUT.json OUTPUT.html", file=sys.stderr)
        return 2
    source, output = map(Path, sys.argv[1:])
    data = json.loads(source.read_text(encoding="utf-8"))
    output.write_text(render(data), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
