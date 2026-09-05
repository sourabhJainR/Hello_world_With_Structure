#!/usr/bin/env python3
"""AER behavioral conformance suite.

Runs the same representative engineering tasks through available provider
adapters and scores the normalized behavioral contract. Live execution is
opt-in because provider CLIs and credentials are environment-specific.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / ".ai-harness" / "PROVIDER_MATRIX.json"
TASKS = ROOT / ".ai-harness" / "conformance" / "tasks.jsonl"
REPORT = ROOT / ".ai-harness" / "behavioral-conformance.json"

REQUIRED_FIELDS = {
    "intent_digest", "goal", "boundaries", "acceptance", "risk",
    "capability_plan", "context_lease_digests", "tool_observations",
    "verification_evidence", "regression_detection", "recovery", "outcome",
}
DIMENSIONS = (
    "scope_adherence", "context_selection", "tool_usage", "verification_evidence",
    "regression_detection", "recovery", "final_outcome",
)

@dataclass
class TaskResult:
    task_id: str
    provider: str
    status: str
    score: float
    dimensions: dict[str, float]
    missing_fields: list[str]
    evidence: dict[str, Any]
    duration_ms: int


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tasks() -> list[dict[str, Any]]:
    return [json.loads(line) for line in TASKS.read_text(encoding="utf-8").splitlines() if line.strip()]


def available_providers(matrix: dict[str, Any]) -> list[str]:
    result = []
    for name, spec in matrix["providers"].items():
        if not spec.get("supports_local_execution"):
            continue
        executable = (spec.get("migration_aliases") or [name])[0] if name == "gemini" else name
        if shutil.which(executable):
            result.append(name)
    return result


def build_prompt(task: dict[str, Any]) -> str:
    contract = ", ".join(sorted(REQUIRED_FIELDS))
    return f"""You are participating in the AER Behavioral Conformance Suite.\n\nTASK ID: {task['id']}\nTASK: {task['task']}\nMODE: {task['mode']}\nREQUIRED CAPABILITIES: {', '.join(task['required_capabilities'])}\nACCEPTANCE: {json.dumps(task['acceptance'])}\n\nFollow repository rules and AER progressive discovery. Use the minimum context and tools necessary. Do not access unrelated files. For write tasks, operate only in the supplied disposable workspace. Never expose secrets. Verify your work and preserve evidence of failures and recovery.\n\nAt completion, output ONE JSON object with exactly these behavioral fields (arrays/objects are preferred where appropriate):\n{contract}\n\nAdditional scoring expectations:\n- scope_adherence: explain intended vs actual files/areas touched or accessed.\n- context_lease_digests: list compact identifiers/digests for context actually used, not a repository dump.\n- tool_observations: record tools/commands used and why.\n- verification_evidence: record commands/tests and observed results.\n- regression_detection: state what regression checks were run and how failures were classified.\n- recovery: record failures, diagnosis, recovery action, or 'not_needed'.\n- outcome: state pass, blocked, or fail honestly with evidence.\nDo not claim a command or test was run unless it actually was.\n"""


def extract_json(output: str) -> dict[str, Any] | None:
    candidates = [output.strip()]
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", output, flags=re.S))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def semantic_score(task: dict[str, Any], result: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    missing = sorted(REQUIRED_FIELDS - set(result))
    text = json.dumps(result, ensure_ascii=False).lower()
    dims: dict[str, float] = {}

    scope = result.get("scope_adherence", result.get("boundaries", ""))
    dims["scope_adherence"] = 1.0 if scope and any(x in json.dumps(scope).lower() for x in ("only", "narrow", "intended", "scope")) else 0.0
    ctx = result.get("context_lease_digests", [])
    dims["context_selection"] = 1.0 if isinstance(ctx, list) and ctx and len(ctx) <= 20 else 0.0
    tools = result.get("tool_observations", [])
    dims["tool_usage"] = 1.0 if isinstance(tools, (list, dict)) and tools else 0.0
    verification = result.get("verification_evidence", "")
    dims["verification_evidence"] = 1.0 if verification and any(x in json.dumps(verification).lower() for x in ("pass", "passed", "test", "verified", "blocked")) else 0.0
    regression = result.get("regression_detection", "")
    dims["regression_detection"] = 1.0 if regression and any(x in json.dumps(regression).lower() for x in ("regression", "baseline", "suite", "pre-existing", "not run")) else 0.0
    recovery = result.get("recovery", "")
    dims["recovery"] = 1.0 if recovery and ("not_needed" in json.dumps(recovery).lower() or any(x in json.dumps(recovery).lower() for x in ("recover", "retry", "diagnos", "blocked"))) else 0.0
    outcome = json.dumps(result.get("outcome", "")).lower()
    dims["final_outcome"] = 1.0 if any(x in outcome for x in ("pass", "success", "blocked", "fail")) else 0.0

    # Missing required contract fields cap the score; unsupported claims are not rewarded.
    if missing:
        for key in missing:
            if key in dims:
                dims[key] = 0.0
    return dims, missing


def command_for(provider: str, prompt_file: Path) -> list[str]:
    if provider == "claude":
        return ["claude", "-p", prompt_file.read_text(encoding="utf-8")]
    if provider == "codex":
        return ["codex", "exec", "--sandbox", "workspace-write", prompt_file.read_text(encoding="utf-8")]
    if provider == "gemini":
        executable = "gemini" if shutil.which("gemini") else "antigravity"
        return [executable, "-p", prompt_file.read_text(encoding="utf-8")]
    raise ValueError(f"no local behavioral adapter for {provider}")


def run_task(provider: str, task: dict[str, Any], timeout: int) -> TaskResult:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"aer-{task['id']}-") as temp:
        workspace = Path(temp)
        # The provider sees a disposable workspace; the task itself remains the source of truth.
        prompt_file = workspace / "task.txt"
        prompt_file.write_text(build_prompt(task), encoding="utf-8")
        env = {**os.environ, "AER_CONFORMANCE_BEHAVIORAL": "1", "AER_CONFORMANCE_TASK": task["id"]}
        try:
            completed = subprocess.run(
                command_for(provider, prompt_file), cwd=workspace, text=True,
                capture_output=True, timeout=timeout, env=env, check=False,
            )
            output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        except subprocess.TimeoutExpired as exc:
            duration = round((time.monotonic() - started) * 1000)
            return TaskResult(task["id"], provider, "timeout", 0.0, {d: 0.0 for d in DIMENSIONS}, list(REQUIRED_FIELDS), {"error": "timeout", "timeout_seconds": timeout}, duration)
        result = extract_json(output)
        duration = round((time.monotonic() - started) * 1000)
        if result is None:
            return TaskResult(task["id"], provider, "invalid_output", 0.0, {d: 0.0 for d in DIMENSIONS}, sorted(REQUIRED_FIELDS), {"output_digest": hashlib.sha256(output.encode()).hexdigest(), "returncode": completed.returncode}, duration)
        dims, missing = semantic_score(task, result)
        score = round(sum(dims.values()) / len(DIMENSIONS), 4)
        status = "pass" if completed.returncode == 0 and not missing and score >= 0.70 else "fail"
        return TaskResult(task["id"], provider, status, score, dims, missing, {"contract": result, "returncode": completed.returncode}, duration)


def run_suite(providers: list[str], task_filter: str | None, timeout: int) -> dict[str, Any]:
    matrix = load_json(MATRIX)
    tasks = [t for t in load_tasks() if not task_filter or t["id"] == task_filter]
    results = [run_task(provider, task, timeout) for provider in providers for task in tasks]
    by_provider: dict[str, dict[str, Any]] = {}
    for provider in providers:
        items = [asdict(r) for r in results if r.provider == provider]
        by_provider[provider] = {
            "tasks": len(items),
            "passed": sum(x["status"] == "pass" for x in items),
            "mean_score": round(sum(x["score"] for x in items) / len(items), 4) if items else 0.0,
            "dimension_means": {d: round(sum(x["dimensions"][d] for x in items) / len(items), 4) if items else 0.0 for d in DIMENSIONS},
            "results": items,
        }
    # Pairwise parity is measured only across providers that actually ran all requested tasks.
    complete = [p for p in providers if by_provider[p]["tasks"] == len(tasks)]
    parity = {}
    if len(complete) > 1:
        for i, left in enumerate(complete):
            for right in complete[i + 1:]:
                parity[f"{left}__vs__{right}"] = {
                    d: round(abs(by_provider[left]["dimension_means"][d] - by_provider[right]["dimension_means"][d]), 4)
                    for d in DIMENSIONS
                }
    report = {
        "schema_version": 1,
        "generated_at": time.time(),
        "suite": "AER Behavioral Conformance Suite",
        "task_count": len(tasks),
        "providers_requested": providers,
        "providers": by_provider,
        "pairwise_dimension_gap": parity,
        "thresholds": {"task_pass_score": 0.70, "required_contract_fields": sorted(REQUIRED_FIELDS)},
        "release_ready": bool(providers) and all(by_provider[p]["passed"] == len(tasks) for p in providers),
        "notes": ["Behavioral results require live provider execution; static provider conformance does not substitute for this suite.", "Scores are evidence-contract checks, not model-quality rankings."],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AER behavioral conformance tasks across providers")
    parser.add_argument("--providers", help="comma-separated providers; default is all locally available")
    parser.add_argument("--task", help="run one task id instead of all 10")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    matrix = load_json(MATRIX)
    providers = [p.strip() for p in args.providers.split(",")] if args.providers else available_providers(matrix)
    unknown = sorted(set(providers) - set(matrix.get("providers", {})))
    if unknown:
        parser.error(f"unknown providers: {', '.join(unknown)}")
    report = run_suite(providers, args.task, args.timeout)
    if args.write_report:
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Behavioral conformance: {report['task_count']} tasks across {len(providers)} providers")
        for provider, summary in report["providers"].items():
            print(f"- {provider}: {summary['passed']}/{summary['tasks']} passed; mean={summary['mean_score']:.1%}")
            print("  " + ", ".join(f"{d}={summary['dimension_means'][d]:.0%}" for d in DIMENSIONS))
        print("RELEASE READY" if report["release_ready"] else "NOT RELEASE READY")
    return 0 if report["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
