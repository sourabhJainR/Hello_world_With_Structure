#!/usr/bin/env python3
"""Deterministic, dependency-free P0 contract/evidence evaluations."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'.ai-harness/runtime'))
from p0 import add_decision, add_evidence, detect_thrash, evidence, new_state, proof_bundle, risk_controls, risk_level, validate_state, verification


def check(name, fn):
    try:
        fn(); return {"id":name,"passed":True}
    except Exception as exc:
        return {"id":name,"passed":False,"error":f"{type(exc).__name__}: {exc}"}


def main():
    results=[
      check("state-contract", lambda: (_ for _ in ()).throw(AssertionError("invalid state")) if validate_state(new_state("E1","goal")) else None),
      check("evidence-decision-trace", lambda: trace()),
      check("verification-trace", lambda: verify_trace()),
      check("risk-escalation", lambda: (lambda level: (_ for _ in ()).throw(AssertionError(level)) if level!="critical" or "isolated_execution" not in risk_controls(level) else None)(risk_level({"security_risk":3}))),
      check("thrash-stop", lambda: (_ for _ in ()).throw(AssertionError("thrash not detected")) if not detect_thrash([{"signature":"same"}]*5)["thrashing"] else None),
      check("proof-determinism", lambda: proof()),
      check("proof-changes-with-state", lambda: proof_changes()),
      check("missing-evidence-rejected", lambda: missing()),
    ]
    passed=sum(x["passed"] for x in results)
    report={"cases":len(results),"passed":passed,"failed":len(results)-passed,"release_ready":passed==len(results),"results":results}
    print(json.dumps(report,indent=2))
    return 0 if report["release_ready"] else 1


def trace():
    s=new_state("E2","goal"); e=evidence("source","x.py","fact","x.py:1","abc","high"); add_evidence(s,e); add_decision(s,"reuse",[e["id"]]); assert not validate_state(s)

def verify_trace():
    s=new_state("E3","goal"); e=evidence("test","test.py","passed","test.py:1","abc","high"); add_evidence(s,e); verification(s,"unit","passed","pytest",[e["id"]]); assert not validate_state(s)

def proof():
    s=new_state("E4","goal"); assert proof_bundle(s)["proof_id"]==proof_bundle(s)["proof_id"]

def proof_changes():
    a=new_state("E5","goal"); b=new_state("E5","different"); assert proof_bundle(a)["proof_id"]!=proof_bundle(b)["proof_id"]

def missing():
    s=new_state("E6","goal")
    try: add_decision(s,"bad",["missing"])
    except ValueError: return
    raise AssertionError("missing evidence accepted")

if __name__=="__main__": raise SystemExit(main())
