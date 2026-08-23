#!/usr/bin/env python3
"""Adaptive, provider-neutral AI coding harness.

The harness is intentionally dependency-free and language-neutral. It routes a
request, builds compact context, executes a configured AI CLI, verifies the
result, records checkpoints, and learns from evidence without self-editing its
own executable code or security policy.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"
CONFIG_PATH = HARNESS / "config.toml"
RUNS = HARNESS / "runs"
MEMORY = HARNESS / "memory"
PROMPTS = HARNESS / "prompts"
PRINCIPLES = HARNESS / "principles.md"
EVALS = HARNESS / "evals" / "cases.jsonl"
CAPABILITIES = ("research", "poc", "grill")
MODES = ("implement", "debug", "research", "poc", "review")
RISKS = ("low", "medium", "high", "critical")
UNCERTAINTIES = ("known", "moderate", "unknown")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def compact(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    head = max(1, int(limit * 0.72))
    tail = max(1, limit - head - 60)
    return text[:head] + "\n... [compacted] ...\n" + text[-tail:]


def ensure_dirs() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    MEMORY.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            items.append(value)
    return items


def run_capture(command: list[str], cwd: Path = ROOT, timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"ERROR: {exc}"
    return (result.stdout or result.stderr).strip()


def git_state() -> str:
    return "\n".join(
        [
            "$ git status --short\n" + run_capture(["git", "status", "--short"]),
            "$ git branch --show-current\n" + run_capture(["git", "branch", "--show-current"]),
            "$ git rev-parse HEAD\n" + run_capture(["git", "rev-parse", "HEAD"]),
        ]
    )


def git_diff_summary() -> str:
    return "\n".join(
        [
            "$ git diff --stat\n" + run_capture(["git", "diff", "--stat"]),
            "$ git diff --check\n" + run_capture(["git", "diff", "--check"]),
            "$ git diff --name-only\n" + run_capture(["git", "diff", "--name-only"]),
        ]
    )


def build_repo_map(limit: int = 500) -> str:
    raw = run_capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"])
    files = [line for line in raw.splitlines() if line][:limit]
    lines = ["# Repository Map", f"Workspace: {ROOT}", ""]
    symbol_pattern = re.compile(
        r"^\s*(?:public |private |protected |internal |static |async |export )*"
        r"(?:class|interface|struct|enum|def|function|func|fn)\s+([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    extensions = {
        ".py", ".cs", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    }
    for rel in files:
        path = ROOT / rel
        if not path.is_file():
            continue
        entry = f"- {rel} ({path.stat().st_size} bytes)"
        if path.suffix.lower() in extensions and path.stat().st_size <= 200_000:
            try:
                symbols = symbol_pattern.findall(path.read_text(encoding="utf-8", errors="ignore"))
                if symbols:
                    entry += " :: " + ", ".join(symbols[:16])
            except OSError:
                pass
        lines.append(entry)
    return "\n".join(lines) + "\n"


def normalize_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    stop = {
        "the", "and", "for", "with", "from", "this", "that", "into", "have",
        "will", "task", "change", "please", "need", "make", "using",
    }
    return {word for word in words if word not in stop}


def relevant_memory(task: str, budget: int) -> str:
    patterns = MEMORY / "patterns.jsonl"
    observations = MEMORY / "observations.jsonl"
    candidates = read_jsonl(patterns) + read_jsonl(observations)
    task_words = normalize_words(task)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in candidates:
        text = " ".join(str(item.get(key, "")) for key in ("pattern", "lesson", "scope", "tags", "task"))
        overlap = len(task_words & normalize_words(text))
        confidence = float(item.get("confidence", 0.5))
        recency_bonus = 0.0 if not item.get("created_at") else 0.25
        score = overlap * 2 + confidence + recency_bonus
        if overlap or confidence >= 0.9:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    lines: list[str] = []
    used = 0
    for _, item in ranked[:12]:
        value = json.dumps(item, ensure_ascii=False)
        if used + len(value) > budget:
            break
        lines.append(value)
        used += len(value)
    return "\n".join(lines) or "No relevant learned patterns."


def load_principles(limit: int = 7000) -> str:
    if not PRINCIPLES.exists():
        return "Use language-neutral judgment focused on correctness, simplicity, maintainability, security, testing, compatibility, failure awareness, and evidence."
    return compact(PRINCIPLES.read_text(encoding="utf-8"), limit)


def applicable_principles(task: str, route: dict[str, Any]) -> list[str]:
    text = task.lower()
    selected = [
        "DRY", "YAGNI", "KISS", "DI / Dependency Inversion", "Separation of Concerns",
        "High Cohesion / Low Coupling", "Compatibility by Default", "Test the Behavior",
        "Evidence over Assumption", "Locality of Change",
    ]
    if route.get("risk") in {"high", "critical"} or any(word in text for word in ("security", "auth", "permission", "secret")):
        selected += ["Security by Default", "Fail Fast and Explicitly", "Least Knowledge", "Least Privilege"]
    if route.get("mode") in {"debug", "poc"} or any(word in text for word in ("concurrency", "timeout", "performance", "scale", "retry")):
        selected += ["Resource and Failure Awareness", "Observability"]
    if route.get("risk") in {"high", "critical"} or any(word in text for word in ("migration", "breaking", "production", "rollout")):
        selected += ["Reversibility", "Make Illegal States Hard to Represent"]
    return list(dict.fromkeys(selected))


def heuristic_route(task: str) -> dict[str, Any]:
    text = task.lower()
    caps: list[str] = []
    risk = "low"
    uncertainty = "known"
    mode = "implement"
    scope = "repository"
    research_terms = ("compare", "evaluate", "research", "unknown", "which library", "which framework", "architecture", "design option", "latest", "investigate")
    poc_terms = ("poc", "proof of concept", "feasibility", "spike", "prototype", "can we", "experiment")
    grill_terms = ("security", "authentication", "authorization", "production", "migration", "breaking change", "performance", "scale", "multi-tenant", "database", "release")
    debug_terms = ("why", "investigate", "diagnose", "intermittent", "root cause", "failing", "hang", "error", "regression", "broken")
    if any(term in text for term in research_terms):
        caps.append("research")
        uncertainty = "moderate"
    if any(term in text for term in poc_terms):
        caps.append("poc")
        uncertainty = "unknown"
    if any(term in text for term in grill_terms):
        caps.append("grill")
        risk = "high"
    if any(term in text for term in debug_terms):
        mode = "debug"
        uncertainty = "moderate"
    if any(term in text for term in ("only research", "research only", "analyze only")):
        mode = "research"
    if any(term in text for term in ("only review", "review only", "review this")):
        mode = "review"
    if any(term in text for term in ("repository", "repo", "cross service", "cross-repo")):
        scope = "repository"
    return {
        "mode": mode,
        "capabilities": list(dict.fromkeys(caps)),
        "risk": risk,
        "uncertainty": uncertainty,
        "scope": scope,
        "reason": "heuristic fallback",
        "confidence": 0.55,
    }


def normalize_route(value: dict[str, Any]) -> dict[str, Any]:
    route = dict(value)
    route["mode"] = route.get("mode") if route.get("mode") in MODES else "implement"
    route["risk"] = route.get("risk") if route.get("risk") in RISKS else "low"
    route["uncertainty"] = route.get("uncertainty") if route.get("uncertainty") in UNCERTAINTIES else "known"
    route["capabilities"] = list(dict.fromkeys([c for c in route.get("capabilities", []) if c in CAPABILITIES]))
    route["scope"] = str(route.get("scope", "repository"))
    route["confidence"] = float(route.get("confidence", 0.5))
    route["reason"] = compact(str(route.get("reason", "")), 300)
    return route


def parse_route_output(output: str) -> dict[str, Any] | None:
    match = re.search(r"ROUTE_JSON\s*:\s*(\{.*?\})(?:\n|$)", output, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return normalize_route(value) if isinstance(value, dict) else None


def make_run_dir() -> Path:
    ensure_dirs()
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS / stamp
    suffix = 1
    while path.exists():
        path = RUNS / f"{stamp}-{suffix}"
        suffix += 1
    path.mkdir(parents=True)
    return path


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def provider_command(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path) -> tuple[list[str], Path]:
    values = {
        "{prompt_file}": str(prompt_file),
        "{workspace}": str(ROOT),
        "{phase}": phase,
        "{run_dir}": str(run_dir),
        "{python}": sys.executable,
    }
    command = [values.get(value, value) for value in provider["command"]]
    working = provider.get("working_directory", "{workspace}")
    cwd = Path(values.get(working, working))
    return command, cwd


def invoke(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path, output_file: Path, timeout: int, dry_run: bool) -> tuple[int, str, float]:
    command, cwd = provider_command(provider, prompt_file, phase, run_dir)
    env = os.environ.copy()
    env.update({
        "AI_HARNESS_RUN_DIR": str(run_dir),
        "AI_HARNESS_PHASE": phase,
        "AI_HARNESS_AGENT": str(provider.get("name", "unknown")),
    })
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        output = "DRY RUN\n$ " + shlex.join(command)
        output_file.write_text(output + "\n", encoding="utf-8")
        return 0, output, 0.0
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = f"TIMEOUT after {timeout}s\n{exc}"
        output_file.write_text(output + "\n", encoding="utf-8")
        return 124, output, time.monotonic() - start
    except OSError as exc:
        output = f"ERROR: {exc}"
        output_file.write_text(output + "\n", encoding="utf-8")
        return 127, output, time.monotonic() - start
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    output_file.write_text(output, encoding="utf-8")
    return result.returncode, output, time.monotonic() - start


def validate_commands(config: dict[str, Any]) -> list[list[str]]:
    raw = config.get("validation", {}).get("commands", [])
    commands: list[list[str]] = []
    for item in raw:
        if isinstance(item, list) and all(isinstance(v, str) for v in item):
            commands.append(item)
        elif isinstance(item, str):
            commands.append(shlex.split(item, posix=os.name != "nt"))
    return commands


def validation(config: dict[str, Any], run_dir: Path, timeout: int) -> tuple[bool, list[dict[str, Any]]]:
    commands = validate_commands(config)
    if not commands:
        return True, []
    log = run_dir / "validation.log"
    results: list[dict[str, Any]] = []
    with log.open("w", encoding="utf-8") as out:
        for command in commands:
            out.write(f"$ {shlex.join(command)}\n")
            started = time.monotonic()
            try:
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=timeout,
                )
                code = result.returncode
                status = "passed" if code == 0 else "failed"
            except subprocess.TimeoutExpired:
                code = 124
                status = "timeout"
            out.write(f"status={status} exit={code}\n\n")
            results.append({"command": command, "status": status, "exit_code": code, "duration_seconds": round(time.monotonic() - started, 3)})
            if code != 0:
                (run_dir / "validation.failed").write_text("failed\n", encoding="utf-8")
                return False, results
    return True, results


def phase_sequence(route: dict[str, Any]) -> list[str]:
    mode = route.get("mode", "implement")
    caps = list(route.get("capabilities", []))
    phases = ["context"]
    if "research" in caps or mode == "research":
        phases.append("research")
    if "poc" in caps or mode == "poc":
        phases.append("poc")
    if mode == "debug":
        phases.append("debug")
    if mode in {"implement", "debug"}:
        phases.extend(["implement", "validate"])
    if mode == "review":
        phases.append("review")
    if "grill" in caps:
        phases.append("grill")
    if mode in {"implement", "debug", "poc"}:
        phases.append("review")
    phases.append("learn")
    return list(dict.fromkeys(phases))


def render_prompt(phase: str, task: str, source: str, jira: str | None, route: dict[str, Any], context: str, memory: str, history: str) -> str:
    phase_file = PROMPTS / f"{phase}.md"
    phase_rules = phase_file.read_text(encoding="utf-8") if phase_file.exists() else ""
    selected = applicable_principles(task, route)
    return f"""# AI Coding Harness

Operate in an existing repository. The rules are language-neutral. Adapt them to the language, runtime, architecture, and conventions already present. Do not introduce framework-specific patterns merely to satisfy a principle name.

## Applicable principles
{', '.join(selected)}

{load_principles()}

## Input
Source: {source}
Jira: {jira or 'none'}
Task:\n{task}

## Route
{json.dumps(route, indent=2)}

## Relevant memory
{memory}

## Repository state
{git_state()}

## Repository map
{context}

## Prior phase evidence
{compact(history or 'none', 5000)}

## Phase rules
{phase_rules}

## Verification contract
Do not claim success based on model confidence. Use command output, tests, repository evidence, or other explicit verification. Inspect the final diff. If verification fails, diagnose before retrying and do not repeat an unchanged failed action.

## Token discipline
Use only the context needed for the current phase. Prefer targeted file reads, current command output, compact summaries, and relevant memory over full transcripts.
"""


def route_task(provider: dict[str, Any], config: dict[str, Any], task: str, source: str, jira: str | None, memory: str, repo_map: str, run_dir: Path, dry_run: bool) -> dict[str, Any]:
    prompt = f"""Route this software-engineering request. Do not modify files. Keep the result language-neutral.

Return exactly one line starting with ROUTE_JSON: followed by a JSON object with:
mode: implement | debug | research | poc | review
capabilities: zero or more of research | poc | grill
risk: low | medium | high | critical
uncertainty: known | moderate | unknown
scope: file | component | service | repository | cross-repository
principles: array of materially relevant engineering principles
reason: <= 300 characters
confidence: 0.0 to 1.0

Use the smallest safe route. Escalate for high risk, high uncertainty, long-horizon work, cross-boundary changes, or repeated verification failures.

Task source: {source}
Jira key: {jira or 'none'}
Task:\n{task}

Relevant memory:\n{compact(memory, int(config.get('router', {}).get('memory_budget', 900)))}

Repository map:\n{compact(repo_map, int(config.get('router', {}).get('context_budget', 1400)))}
"""
    prompt_file = run_dir / "route.prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    output_file = run_dir / "route.output.md"
    timeout = int(config.get("execution", {}).get("provider_timeout_seconds", 900))
    _, output, duration = invoke(provider, prompt_file, "route", run_dir, output_file, timeout, dry_run)
    parsed = parse_route_output(output)
    route = parsed or normalize_route(heuristic_route(task))
    route["router_duration_seconds"] = round(duration, 3)
    return route


def checkpoint(run_dir: Path, state: dict[str, Any]) -> None:
    write_json(run_dir / "checkpoint.json", state)


def checkpoint_state(manifest: dict[str, Any], phase: str, status: str, next_phase: str | None) -> dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "updated_at": now_iso(),
        "phase": phase,
        "status": status,
        "next_phase": next_phase,
        "route": manifest.get("route", {}),
        "completed_phases": manifest.get("completed_phases", []),
    }


def learn_from_run(run_dir: Path, task: str, route: dict[str, Any], manifest: dict[str, Any]) -> None:
    observations = MEMORY / "observations.jsonl"
    patterns = MEMORY / "patterns.jsonl"
    review = (run_dir / "review.output.md").read_text(encoding="utf-8") if (run_dir / "review.output.md").exists() else ""
    validation_ok = bool(manifest.get("validation", {}).get("passed", True))
    lesson_candidates = []
    for line in review.splitlines():
        clean = line.strip(" -#")
        lower = clean.lower()
        if clean and any(word in lower for word in ("lesson", "recommend", "avoid", "prefer", "risk", "root cause")):
            lesson_candidates.append(compact(clean, 500))
    observation = {
        "id": hashlib.sha256(f"{task}|{now_iso()}".encode()).hexdigest()[:12],
        "created_at": now_iso(),
        "task": compact(task, 500),
        "route": route,
        "provider": manifest.get("provider"),
        "validation_passed": validation_ok,
        "retries": manifest.get("retries", 0),
        "lessons": lesson_candidates[:5],
    }
    append_jsonl(observations, observation)
    for lesson in lesson_candidates[:5]:
        append_jsonl(
            patterns,
            {
                "id": hashlib.sha256(lesson.encode()).hexdigest()[:12],
                "created_at": now_iso(),
                "pattern": lesson,
                "scope": route.get("scope", "repository"),
                "confidence": 0.6 if validation_ok else 0.35,
                "success": validation_ok,
            },
        )


def groom_memory(config: dict[str, Any]) -> dict[str, Any]:
    patterns_path = MEMORY / "patterns.jsonl"
    items = read_jsonl(patterns_path)
    max_items = int(config.get("learning", {}).get("max_memory_items", 250))
    min_obs = int(config.get("learning", {}).get("min_observations_for_promotion", 3))
    success_floor = float(config.get("learning", {}).get("min_success_rate_for_promotion", 0.75))
    observations = read_jsonl(MEMORY / "observations.jsonl")
    counts: dict[str, list[bool]] = {}
    for item in observations:
        for lesson in item.get("lessons", []):
            key = str(lesson)
            counts.setdefault(key, []).append(bool(item.get("validation_passed", False)))
    trusted: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("pattern", ""))
        history = counts.get(key, [])
        if len(history) >= min_obs and (sum(history) / len(history)) >= success_floor:
            promoted = dict(item)
            promoted["status"] = "trusted"
            promoted["confidence"] = min(0.99, max(float(item.get("confidence", 0.5)), sum(history) / len(history)))
            trusted.append(promoted)
        if len(trusted) >= max_items:
            break
    if trusted:
        patterns_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in trusted), encoding="utf-8")
    return {"patterns": len(items), "trusted": len(trusted)}


def load_eval_cases() -> list[dict[str, Any]]:
    return read_jsonl(EVALS)


def run_evals() -> dict[str, Any]:
    cases = load_eval_cases()
    results = []
    for case in cases:
        route = normalize_route(heuristic_route(str(case.get("task", ""))))
        expected = set(case.get("must_include", []))
        observed = set(route.get("capabilities", []))
        results.append({"id": case.get("id"), "passed": expected.issubset(observed), "expected": sorted(expected), "observed": sorted(observed)})
    passed = sum(1 for item in results if item["passed"])
    return {"cases": len(results), "passed": passed, "failed": len(results) - passed, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptive provider-neutral AI coding harness")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("providers")
    sub.add_parser("capabilities")
    sub.add_parser("context")
    sub.add_parser("memory")
    sub.add_parser("groom")
    sub.add_parser("eval")

    run = sub.add_parser("run")
    run.add_argument("--task", default="")
    run.add_argument("--jira")
    run.add_argument("--jira-file")
    run.add_argument("--agent", help="Configured provider; defaults to config.toml")
    run.add_argument("--workflow")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--resume", help="Existing run directory to resume from checkpoint.json")

    args = parser.parse_args()
    config = load_config()

    if args.action == "providers":
        print("\n".join(config.get("providers", {}).keys()))
        return 0
    if args.action == "capabilities":
        print("\n".join(CAPABILITIES))
        return 0
    if args.action == "context":
        target = HARNESS / "repository-map.md"
        target.write_text(build_repo_map(), encoding="utf-8")
        print(target)
        return 0
    if args.action == "memory":
        for path in (MEMORY / "patterns.jsonl", MEMORY / "observations.jsonl"):
            if path.exists():
                print(path.read_text(encoding="utf-8"), end="")
        return 0
    if args.action == "groom":
        print(json.dumps(groom_memory(config), indent=2))
        return 0
    if args.action == "eval":
        print(json.dumps(run_evals(), indent=2))
        return 0

    providers = config.get("providers", {})
    provider_name = args.agent or config.get("harness", {}).get("default_provider", next(iter(providers), ""))
    if provider_name not in providers:
        print(f"Unknown provider: {provider_name}", file=sys.stderr)
        return 2
    provider = dict(providers[provider_name])
    provider["name"] = provider_name

    task = args.task.strip()
    source = "prompt"
    if args.jira_file:
        jira_path = Path(args.jira_file)
        if not jira_path.is_file():
            print(f"Jira file not found: {jira_path}", file=sys.stderr)
            return 2
        task = (task + "\n\nJira context:\n" + jira_path.read_text(encoding="utf-8")).strip()
        source = "jira-file"
    elif args.jira:
        source = "jira"
        task = (task or f"Work on Jira item {args.jira}").strip()
    if not task:
        print("A task, Jira key, or Jira file is required", file=sys.stderr)
        return 2

    if args.resume:
        run_dir = Path(args.resume).resolve()
        if not run_dir.is_dir():
            print(f"Resume directory not found: {run_dir}", file=sys.stderr)
            return 2
        checkpoint_path = run_dir / "checkpoint.json"
        if not checkpoint_path.exists():
            print("checkpoint.json not found", file=sys.stderr)
            return 2
        checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        route = normalize_route(manifest["route"])
        phases = manifest.get("phases", phase_sequence(route))
        start_index = phases.index(checkpoint_data.get("next_phase")) if checkpoint_data.get("next_phase") in phases else 0
        phases = phases[start_index:]
    else:
        run_dir = make_run_dir()
        manifest = {
            "version": 3,
            "run_id": run_dir.name,
            "started_at": now_iso(),
            "provider": provider_name,
            "task": task,
            "source": source,
            "jira": args.jira,
            "completed_phases": [],
            "retries": 0,
        }
        repo_map = build_repo_map()
        memory = relevant_memory(task, int(config.get("router", {}).get("memory_budget", 900)))
        route = route_task(provider, config, task, source, args.jira, memory, repo_map, run_dir, args.dry_run)
        manifest["route"] = route
        manifest["applicable_principles"] = applicable_principles(task, route)
        manifest["phases"] = phase_sequence(route)
        write_json(run_dir / "manifest.json", manifest)
        (run_dir / "task.txt").write_text(task, encoding="utf-8")
        (run_dir / "repository-map.md").write_text(repo_map, encoding="utf-8")
        checkpoint(run_dir, checkpoint_state(manifest, "route", "completed", manifest["phases"][0]))
        phases = manifest["phases"]

    history: list[str] = []
    phase_timeout = int(config.get("execution", {}).get("phase_timeout_seconds", 1200))
    max_retries = int(config.get("execution", {}).get("max_phase_retries", 1))

    for index, phase in enumerate(phases):
        if phase == "context":
            manifest["context_ready"] = True
            manifest["completed_phases"].append(phase)
            checkpoint(run_dir, checkpoint_state(manifest, phase, "completed", phases[index + 1] if index + 1 < len(phases) else None))
            continue
        if phase == "learn":
            learn_from_run(run_dir, task, route, manifest)
            manifest["completed_phases"].append(phase)
            checkpoint(run_dir, checkpoint_state(manifest, phase, "completed", None))
            break
        if phase == "validate":
            passed, results = validation(config, run_dir, phase_timeout)
            manifest["validation"] = {"passed": passed, "results": results}
            write_json(run_dir / "manifest.json", manifest)
            manifest["completed_phases"].append(phase)
            if not passed:
                repair_prompt = run_dir / "repair.prompt.md"
                repair_prompt.write_text(render_prompt("repair", task, source, args.jira, route, (run_dir / "repository-map.md").read_text(encoding="utf-8"), relevant_memory(task, 700), "\n\n".join(history)), encoding="utf-8")
                output_file = run_dir / "repair.output.md"
                for attempt in range(max_retries):
                    manifest["retries"] += 1
                    code, output, _ = invoke(provider, repair_prompt, "repair", run_dir, output_file, phase_timeout, args.dry_run)
                    history.append(compact(output, 2000))
                    if code == 0:
                        passed, results = validation(config, run_dir, phase_timeout)
                        manifest["validation"] = {"passed": passed, "results": results}
                        if passed:
                            break
                if not manifest.get("validation", {}).get("passed", False):
                    checkpoint(run_dir, checkpoint_state(manifest, phase, "blocked", "repair"))
                    write_json(run_dir / "manifest.json", manifest)
                    return 1
            checkpoint(run_dir, checkpoint_state(manifest, phase, "completed", phases[index + 1] if index + 1 < len(phases) else None))
            continue
        if phase == "review" and not any(p in manifest["completed_phases"] for p in ("implement", "debug", "poc")) and route.get("mode") != "review":
            continue
        prompt = run_dir / f"{phase}.prompt.md"
        context = (run_dir / "repository-map.md").read_text(encoding="utf-8")
        memory = relevant_memory(task, int(config.get("router", {}).get("memory_budget", 900)))
        prompt.write_text(render_prompt(phase, task, source, args.jira, route, context, memory, "\n\n".join(history)), encoding="utf-8")
        output_file = run_dir / f"{phase}.output.md"
        succeeded = False
        for attempt in range(max_retries + 1):
            if attempt:
                manifest["retries"] += 1
            code, output, duration = invoke(provider, prompt, phase, run_dir, output_file, phase_timeout, args.dry_run)
            history.append(compact(f"[{phase}] {output}", 2500))
            manifest.setdefault("phase_metrics", {})[phase] = {"duration_seconds": round(duration, 3), "exit_code": code, "attempt": attempt}
            if code == 0:
                succeeded = True
                break
            if attempt < max_retries:
                prompt.write_text(render_prompt(phase, task, source, args.jira, route, context, memory, "\n\n".join(history) + "\nPrevious attempt failed; diagnose before retrying."), encoding="utf-8")
        if not succeeded:
            checkpoint(run_dir, checkpoint_state(manifest, phase, "failed", phase))
            write_json(run_dir / "manifest.json", manifest)
            return 1
        if phase in {"implement", "debug", "poc", "research", "grill", "review"}:
            manifest.setdefault("git_evidence", {})[phase] = git_diff_summary()
        manifest["completed_phases"].append(phase)
        write_json(run_dir / "manifest.json", manifest)
        checkpoint(run_dir, checkpoint_state(manifest, phase, "completed", phases[index + 1] if index + 1 < len(phases) else None))

    final_diff = git_diff_summary()
    manifest["git_final"] = git_state()
    manifest["git_diff"] = final_diff
    manifest["completed_at"] = now_iso()
    manifest["status"] = "completed"
    write_json(run_dir / "manifest.json", manifest)
    checkpoint(run_dir, checkpoint_state(manifest, "complete", "completed", None))
    print(f"Run complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
