#!/usr/bin/env python3
"""CLI for P0 runtime artifacts. Uses only the Python standard library."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))
from p0 import add_decision, add_evidence, detect_thrash, evidence, new_state, proof_bundle, risk_controls, risk_level, save_json, validate_state, verification

def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("task_id"); n.add_argument("goal"); n.add_argument("--source", default="user"); n.add_argument("--out", type=Path, default=Path(".ai-harness/state.json"))
    e = sub.add_parser("evidence"); e.add_argument("state", type=Path); e.add_argument("kind"); e.add_argument("source"); e.add_argument("claim"); e.add_argument("--locator", default=""); e.add_argument("--snapshot", default=""); e.add_argument("--confidence", choices=["high","medium","low"], default="medium")
    d = sub.add_parser("decision"); d.add_argument("state", type=Path); d.add_argument("decision"); d.add_argument("evidence_ids", nargs="+")
    v = sub.add_parser("verify"); v.add_argument("state", type=Path); v.add_argument("kind"); v.add_argument("status", choices=["passed","failed","skipped","unknown"]); v.add_argument("--command", default=""); v.add_argument("--evidence", nargs="*", default=[]); v.add_argument("--details", default="")
    r = sub.add_parser("risk"); r.add_argument("scores", nargs="+", metavar="FIELD=0..3")
    t = sub.add_parser("thrash"); t.add_argument("signatures", nargs="+")
    b = sub.add_parser("proof"); b.add_argument("state", type=Path); b.add_argument("--out", type=Path)
    c = sub.add_parser("check"); c.add_argument("state", type=Path)
    a = p.parse_args()
    if a.cmd == "new": save_json(a.out, new_state(a.task_id, a.goal, a.source)); print(a.out); return 0
    if a.cmd == "risk":
        scores = {x.split("=",1)[0]: int(x.split("=",1)[1]) for x in a.scores}; level = risk_level(scores); print(json.dumps({"level": level, "controls": risk_controls(level)}, indent=2)); return 0
    if a.cmd == "thrash": print(json.dumps(detect_thrash([{ "signature": x } for x in a.signatures]), indent=2)); return 0
    state = json.loads(a.state.read_text(encoding="utf-8"))
    if a.cmd == "evidence": add_evidence(state, evidence(a.kind, a.source, a.claim, a.locator, a.snapshot, a.confidence)); save_json(a.state, state); return 0
    if a.cmd == "decision": add_decision(state, a.decision, a.evidence_ids); save_json(a.state, state); return 0
    if a.cmd == "verify": verification(state, a.kind, a.status, a.command, a.evidence, a.details); save_json(a.state, state); return 0
    if a.cmd == "proof":
        result = proof_bundle(state); out = a.out or a.state.with_name("proof-bundle.json"); save_json(out, result); print(out); return 0
    errors = validate_state(state); print("VALID" if not errors else "INVALID\n" + "\n".join(errors)); return 0 if not errors else 1
if __name__ == "__main__": raise SystemExit(main())
