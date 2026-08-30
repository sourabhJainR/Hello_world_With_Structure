#!/usr/bin/env python3
"""Run deterministic, dependency-free harness routing and policy evaluations."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"
CASES = HARNESS / "evals" / "cases.jsonl"
SKILLS = [
    ROOT / "skills/ai-coding-orchestrator/SKILL.md",
    ROOT / ".agents/skills/ai-coding-orchestrator/SKILL.md",
    ROOT / ".claude/skills/ai-coding-orchestrator/SKILL.md",
]


def load_cases() -> list[dict]:
    cases = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def load_heuristic_route(task: str) -> dict:
    sys.path.insert(0, str(HARNESS))
    from engine import heuristic_route
    return heuristic_route(task)


def policy_checks() -> list[str]:
    failures: list[str] = []
    shared = ("Engineering State Ledger", "repository-aware", "minimal safe change", "regression", "evidence", "optional")
    for path in SKILLS:
        if not path.exists():
            failures.append(f"missing skill: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            failures.append(f"missing frontmatter: {path}")
            continue
        if not re.search(r"(?m)^name:\s*ai-coding-orchestrator\s*$", text):
            failures.append(f"invalid skill name: {path}")
        if not re.search(r"(?m)^description:\s*\S", text):
            failures.append(f"missing skill description: {path}")
        if len(text) > 9000:
            failures.append(f"skill context budget exceeded: {path} ({len(text)} chars)")
        for marker in shared:
            if marker.lower() not in text.lower():
                failures.append(f"shared contract marker missing: {path}: {marker}")
    plugin = ROOT / ".claude-plugin/plugin.json"
    marketplace = ROOT / ".claude-plugin/marketplace.json"
    if not plugin.exists() or not marketplace.exists():
        failures.append("plugin or marketplace manifest missing")
    return failures


def evaluate_case(case: dict) -> tuple[bool, list[str]]:
    route = load_heuristic_route(case["prompt"])
    problems: list[str] = []
    if route["mode"] != case["expected_mode"]:
        problems.append(f"mode expected={case['expected_mode']} actual={route['mode']}")
    selected = set(route.get("capabilities", []))
    required = set(case.get("required_capabilities", case.get("capabilities", [])))
    forbidden = set(case.get("forbidden_capabilities", []))
    missing = required - selected
    extra = selected & forbidden
    if missing:
        problems.append(f"missing capabilities={sorted(missing)}")
    if extra:
        problems.append(f"forbidden capabilities={sorted(extra)}")
    return not problems, problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic AI Coding Orchestrator evals")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    results = []
    for case in load_cases():
        passed, problems = evaluate_case(case)
        results.append({"id": case["id"], "passed": passed, "problems": problems})

    policy_failures = policy_checks()
    passed = sum(item["passed"] for item in results)
    total = len(results)
    report = {
        "cases": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "policy_failures": policy_failures,
        "release_ready": passed == total and not policy_failures,
        "results": results,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Routing evals: {passed}/{total} passed ({report['accuracy']:.1%})")
        for item in results:
            status = "PASS" if item["passed"] else "FAIL"
            suffix = f": {'; '.join(item['problems'])}" if item["problems"] else ""
            print(f"{status} {item['id']}{suffix}")
        if policy_failures:
            print("Policy failures:")
            for failure in policy_failures:
                print(f"- {failure}")
        print("RELEASE READY" if report["release_ready"] else "NOT RELEASE READY")
    return 0 if report["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
