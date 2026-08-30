#!/usr/bin/env python3
"""Deterministic, dependency-free P2 contract evaluations."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.ai-harness' / 'runtime'))
from p2 import compare_eval_baseline, memory_is_active, memory_record, predict_change_risk, route_model, select_memory


def check(name, fn):
    try:
        fn()
        return {"id": name, "passed": True}
    except Exception as exc:
        return {"id": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"}


def main():
    records = [memory_record("architecture", "ports-and-adapters", "review:1", 0.95, ttl_seconds=60), memory_record("architecture", "legacy", "review:0", 0.5)]
    results = [
        check("model-routing-quality", lambda: _assert(route_model({"scope": 3, "blast_radius": 2, "uncertainty": 2, "requires_reasoning": True}, [{"name": "fast", "quality": .7, "latency_ms": 100, "cost_per_1k": .1, "fast": True, "capabilities": ["reasoning"]}, {"name": "deep", "quality": .95, "latency_ms": 500, "cost_per_1k": .8, "capabilities": ["reasoning"]}])["selected"] == "deep")),
        check("model-routing-negative", lambda: _assert(route_model({"requires_code": True}, [{"name": "chat", "quality": 1, "capabilities": ["reasoning"]}])["selected"] is None)),
        check("memory-expiry", lambda: _assert(memory_is_active(records[0], records[0]["created_at"] + 61) is False)),
        check("memory-bounded-selection", lambda: _assert(len(select_memory(records, "architecture", records[0]["created_at"], 1)) == 1)),
        check("risk-critical", lambda: _assert(predict_change_risk(["api.py", "schema.sql"], fanout=25, coverage=.4, api_change=True, schema_change=True, historical_defects=2)["level"] == "critical")),
        check("risk-low", lambda: _assert(predict_change_risk(["README.md"], coverage=1.0)["level"] == "low")),
        check("eval-regression-blocks-promotion", lambda: _assert(compare_eval_baseline({"accuracy": .95}, {"accuracy": .94})["promotable"] is False)),
        check("eval-improvement-allows-promotion", lambda: _assert(compare_eval_baseline({"accuracy": .95}, {"accuracy": .96})["promotable"] is True)),
    ]
    passed = sum(r["passed"] for r in results)
    report = {"cases": len(results), "passed": passed, "failed": len(results) - passed, "release_ready": passed == len(results), "results": results}
    print(json.dumps(report, indent=2))
    return 0 if report["release_ready"] else 1


def _assert(condition):
    if not condition:
        raise AssertionError


if __name__ == "__main__":
    raise SystemExit(main())
