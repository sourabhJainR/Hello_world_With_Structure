#!/usr/bin/env python3
"""Validate vendored agency specialist contracts and registry integrity."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

REQUIRED = ["Identity & Memory", "Core Mission", "Critical Rules", "Technical Deliverables", "Workflow Process", "Communication Style", "Success Metrics"]

def main():
    root=Path("agency/agents")
    reg=Path("agency/registry.json")
    if not reg.exists(): print("agency registry missing; run sync first"); return 1
    data=json.loads(reg.read_text(encoding="utf-8")); errors=[]
    for a in data.get("agents",[]):
        p=Path(a["file"]); 
        if not p.exists(): errors.append(f"missing: {p}"); continue
        raw=p.read_bytes(); text=raw.decode("utf-8")
        if hashlib.sha256(raw).hexdigest()!=a.get("sha256"): errors.append(f"hash mismatch: {p}")
        if not text.startswith("---\n") or "\n---" not in text: errors.append(f"frontmatter missing: {p}")
        body=text[text.find("\n---",4)+4:]
        headings=[re.sub(r"^[^A-Za-z0-9]+","",h).strip().lower() for h in re.findall(r"^##\s+(.+)$",body,re.M)]
        for h in REQUIRED:
            if not any(h.lower() in x for x in headings): errors.append(f"{p}: missing section {h}")
    if not root.exists(): errors.append("agency/agents missing")
    if errors:
        print("\n".join(errors)); return 1
    print(f"agency validation passed: {len(data.get('agents',[]))} agents")
    return 0
if __name__=="__main__": sys.exit(main())
