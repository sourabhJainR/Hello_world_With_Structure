#!/usr/bin/env python3
"""Adaptive provider-neutral AI coding harness.

Python 3.11+; standard library only.
The harness routes tasks, compacts context, executes a selected AI CLI,
records evidence, and learns reusable patterns without rewriting its own code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"
CONFIG_PATH = HARNESS / "config.toml"
RUNS = HARNESS / "runs"
MEMORY = HARNESS / "memory"
PROMPTS = HARNESS / "prompts"

CAPABILITIES = ("research", "poc", "grill")
DEFAULT_ROUTE = {"mode": "implement", "capabilities": [], "risk": "low", "uncertainty": "known"}


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def run_capture(command: list[str], cwd: Path = ROOT) -> str:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    except OSError as exc:
        return f"ERROR: {exc}"
    return (result.stdout or result.stderr).strip()


def git_state() -> str:
    return "\n".join([
        "$ git status --short\n" + run_capture(["git", "status", "--short"]),
        "$ git branch --show-current\n" + run_capture(["git", "branch", "--show-current"]),
        "$ git rev-parse HEAD\n" + run_capture(["git", "rev-parse", "HEAD"]),
    ])


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


def memory_paths() -> tuple[Path, Path]:
    ensure_dirs()
    return MEMORY / "patterns.jsonl", MEMORY / "observations.jsonl"


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                items.append(item)
        except json.JSONDecodeError:
            continue
    return items


def normalize_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "have", "will", "task", "change"}
    return {w for w in words if w not in stop}


def build_repo_map(limit: int = 500) -> str:
    raw = run_capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"])
    files = [line for line in raw.splitlines() if line][:limit]
    lines = ["# Repository Map", f"Workspace: {ROOT}", ""]
    pattern = re.compile(
        r"^\s*(?:public |private |protected |internal |static |async |export )*"
        r"(?:class|interface|struct|enum|def|function|func|fn)\s+([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    extensions = {".py", ".cs", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp"}
    for rel in files:
        path = ROOT / rel
        if not path.is_file():
            continue
        entry = f"- {rel} ({path.stat().st_size} bytes)"
        if path.suffix.lower() in extensions and path.stat().st_size <= 200_000:
            try:
                symbols = pattern.findall(path.read_text(encoding="utf-8", errors="ignore"))
                if symbols:
                    entry += " :: " + ", ".join(symbols[:16])
            except OSError:
                pass
        lines.append(entry)
    return "\n".join(lines) + "\n"


def relevant_memory(task: str, budget: int) -> str:
    patterns, observations = memory_paths()
    candidates = read_jsonl(patterns) + read_jsonl(observations)
    task_words = normalize_words(task)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in candidates:
        words = normalize_words(" ".join(str(item.get(k, "")) for k in ("pattern", "lesson", "scope", "tags")))
        overlap = len(task_words & words)
        confidence = float(item.get("confidence", 0.5))
        score = overlap * 2 + confidence
        if overlap or confidence >= 0.9:
            ranked.append((score, item))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return "No relevant learned patterns."
    lines: list[str] = []
    used = 0
    for _, item in ranked[:12]:
        value = json.dumps(item, ensure_ascii=False)
        if used + len(value) > budget:
            break
        lines.append(value)
        used += len(value)
    return "\n".join(lines) or "No relevant learned patterns."


def heuristic_route(task: str) -> dict[str, Any]:
    text = task.lower()
    caps: list[str] = []
    risk = "low"
    uncertainty = "known"
    mode = "implement"
    if any(x in text for x in ("compare", "evaluate", "research", "unknown", "which library", "which framework", "architecture", "design option")):
        caps.append("research")
        uncertainty = "moderate"
    if any(x in text for x in ("poc", "proof of concept", "feasibility", "spike", "prototype", "can we", "experiment")):
        caps.append("poc")
        uncertainty = "unknown"
    if any(x in text for x in ("security", "authentication", "authorization", "production", "migration", "breaking change", "performance", "scale", "multi-tenant", "database")):
        caps.append("grill")
        risk = "high"
    if any(x in text for x in ("why", "investigate", "diagnose", "intermittent", "root cause", "failing", "hang", "error")):
        mode = "debug"
        uncertainty = "moderate"
    if any(x in text for x in ("only research", "research only", "analyze only")):
        mode = "research"
    if any(x in text for x in ("only review", "review only", "review this")):
        mode = "review"
    return {"mode": mode, "capabilities": list(dict.fromkeys(caps)), "risk": risk, "uncertainty": uncertainty, "reason": "heuristic fallback"}


def parse_route_output(output: str) -> dict[str, Any] | None:
    match = re.search(r"ROUTE_JSON\s*:\s*(\{.*\})", output, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    caps = [c for c in value.get("capabilities", []) if c in CAPABILITIES]
    value["capabilities"] = list(dict.fromkeys(caps))
    value["mode"] = str(value.get("mode", "implement"))
    value["risk"] = str(value.get("risk", "low"))
    value["uncertainty"] = str(value.get("uncertainty", "known"))
    return value


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


def provider_command(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path) -> tuple[list[str], Path]:
    values = {
        "{prompt_file}": str(prompt_file),
        "{workspace}": str(ROOT),
        "{phase}": phase,
        "{run_dir}": str(run_dir),
    }
    command = [values.get(v, v) for v in provider["command"]]
    cwd = Path(values.get(provider.get("working_directory", "{workspace}"), provider.get("working_directory", str(ROOT))))
    return command, cwd


def invoke(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path, output_file: Path, dry_run: bool) -> tuple[int, str]:
    command, cwd = provider_command(provider, prompt_file, phase, run_dir)
    env = os.environ.copy()
    env.update({"AI_HARNESS_RUN_DIR": str(run_dir), "AI_HARNESS_PHASE": phase, "AI_HARNESS_AGENT": provider.get("name", "unknown")})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        output = "DRY RUN\n$ " + " ".join(command)
        output_file.write_text(output + "\n", encoding="utf-8")
        return 0, output
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    except OSError as exc:
        output = f"ERROR: {exc}"
        output_file.write_text(output + "\n", encoding="utf-8")
        return 127, output
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    output_file.write_text(output, encoding="utf-8")
    return result.returncode, output


def render_prompt(phase: str, task: str, source: str, jira: str | None, route: dict[str, Any], context: str, memory: str, history: str) -> str:
    phase_path = PROMPTS / f"{phase}.md"
    phase_rules = phase_path.read_text(encoding="utf-8") if phase_path.exists() else ""
    return f"""# AI Coding Harness

You are operating inside an existing repository. Inspect before changing code. Keep outputs concise and factual.

## Input
Source: {source}
Jira: {jira or 'none'}
Task:
{task}

## Route
{json.dumps(route, indent=2)}

## Relevant memory
{memory}

## Repository state
{git_state()}

## Repository map
{context}

## Prior phase evidence
{history or 'none'}

## Phase rules
{phase_rules}

## Token discipline
Use the smallest amount of context needed. Prefer targeted file reads over broad dumps. Summarize completed work for the next phase. Never claim a command or source was used unless it was used.
"""


def route_task(provider: dict[str, Any], task: str, source: str, jira: str | None, memory: str, repo_map: str, run_dir: Path, dry_run: bool) -> dict[str, Any]:
    prompt = f"""Route this software-engineering request. Do not modify files.

Return exactly one line starting with ROUTE_JSON: followed by JSON with:
mode: one of implement, debug, research, poc, review
capabilities: zero or more of research, poc, grill
risk: low, medium, high, critical
uncertainty: known, moderate, unknown
scope: file, component, service, repository, cross-repository
reason: <= 300 characters

Input source: {source}
Jira key: {jira or 'none'}
Task:
{task}

Relevant memory:
{compact(memory, 1800)}

Repository map:
{compact(repo_map, 2200)}
"""
    route_file = run_dir / "route.prompt.md"
    route_file.write_text(prompt, encoding="utf-8")
    output_file = run_dir / "route.output.md"
    code, output = invoke(provider, route_file, "route", run_dir, output_file, dry_run)
    parsed = parse_route_output(output)
    if parsed:
        return parsed
    return heuristic_route(task)


def validation(config: dict[str, Any], run_dir: Path) -> bool:
    commands = config.get("validation", {}).get("commands", [])
    if not commands:
        return True
    log = run_dir / "validation.log"
    with log.open("w", encoding="utf-8") as out:
        for command in commands:
            out.write(f"$ {command}\n")
            result = subprocess.run(command, cwd=ROOT, shell=True, text=True, stdout=out, stderr=subprocess.STDOUT, check=False)
            out.write(f"exit={result.returncode}\n\n")
            if result.returncode != 0:
                return False
    return True


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


def learn_from_run(run_dir: Path, task: str, route: dict[str, Any]) -> None:
    patterns_path, observations_path = memory_paths()
    review = (run_dir / "review.output.md").read_text(encoding="utf-8") if (run_dir / "review.output.md").exists() else ""
    validation_ok = not (run_dir / "validation.failed").exists()
    lesson_candidates = []
    if review:
        lines = [line.strip(" -#") for line in review.splitlines() if line.strip()]
        for line in lines:
            if any(word in line.lower() for word in ("lesson", "recommend", "avoid", "prefer", "risk")):
                lesson_candidates.append(line[:500])
    observation = {
        "id": hashlib.sha256(f"{task}|{now_iso()}".encode()).hexdigest()[:12],
        "created_at": now_iso(),
        "task": compact(task, 500),
        "route": route,
        "success": validation_ok,
        "lessons": lesson_candidates[:5],
    }
    append_jsonl(observations_path, observation)
    for lesson in lesson_candidates[:5]:
        append_jsonl(patterns_path, {
            "id": hashlib.sha256(lesson.encode()).hexdigest()[:12],
            "created_at": now_iso(),
            "pattern": lesson,
            "scope": route.get("scope", "repository"),
            "confidence": 0.55,
            "observations": 1,
            "successes": 1 if validation_ok else 0,
            "source": "run-review",
        })


def groom(config: dict[str, Any]) -> dict[str, int]:
    patterns_path, _ = memory_paths()
    items = read_jsonl(patterns_path)
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = re.sub(r"\s+", " ", str(item.get("pattern", "")).strip().lower())
        if not key:
            continue
        current = grouped.get(key)
        if not current:
            current = dict(item)
            current["observations"] = 0
            current["successes"] = 0
            grouped[key] = current
        current["observations"] += int(item.get("observations", 1))
        current["successes"] += int(item.get("successes", 0))
        current["confidence"] = max(float(current.get("confidence", 0.5)), float(item.get("confidence", 0.5)))
        current["last_seen"] = item.get("created_at", current.get("last_seen"))
    min_obs = int(config.get("learning", {}).get("min_observations_for_promotion", 3))
    min_rate = float(config.get("learning", {}).get("min_success_rate_for_promotion", 0.75))
    output: list[dict[str, Any]] = []
    promoted = 0
    for item in grouped.values():
        obs = max(1, int(item.get("observations", 1)))
        rate = int(item.get("successes", 0)) / obs
        item["success_rate"] = round(rate, 3)
        item["confidence"] = round(min(0.99, max(item.get("confidence", 0.5), rate)), 3)
        item["status"] = "trusted" if obs >= min_obs and rate >= min_rate else "observed"
        if item["status"] == "trusted":
            promoted += 1
        output.append(item)
    output.sort(key=lambda x: (x.get("status") == "trusted", x.get("confidence", 0)), reverse=True)
    max_items = int(config.get("learning", {}).get("max_memory_items", 250))
    output = output[:max_items]
    with patterns_path.open("w", encoding="utf-8") as handle:
        for item in output:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"patterns": len(output), "trusted": promoted}


def memory_summary() -> str:
    patterns, observations = memory_paths()
    p = read_jsonl(patterns)
    o = read_jsonl(observations)
    trusted = [x for x in p if x.get("status") == "trusted"]
    return json.dumps({"patterns": len(p), "trusted": len(trusted), "observations": len(o), "trusted_items": trusted[:20]}, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptive provider-neutral AI coding harness")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("providers")
    sub.add_parser("capabilities")
    sub.add_parser("memory")
    sub.add_parser("groom")
    sub.add_parser("context")
    run = sub.add_parser("run")
    run.add_argument("--agent", default=None)
    run.add_argument("--task", default=None)
    run.add_argument("--jira", default=None)
    run.add_argument("--jira-file", default=None)
    run.add_argument("--source", default="prompt")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--workflow", default=None)
    args = parser.parse_args()

    config = load_config()
    if args.command == "providers":
        print("\n".join(config.get("providers", {}).keys()))
        return 0
    if args.command == "capabilities":
        print("\n".join(CAPABILITIES))
        return 0
    if args.command == "memory":
        print(memory_summary())
        return 0
    if args.command == "groom":
        print(json.dumps(groom(config), indent=2))
        return 0
    if args.command == "context":
        print(build_repo_map())
        return 0

    if not args.task and not args.jira and not args.jira_file:
        print("Provide --task, --jira, or --jira-file", file=sys.stderr)
        return 2

    task = args.task or ""
    if args.jira_file:
        path = Path(args.jira_file)
        task += "\n\nJira content:\n" + path.read_text(encoding="utf-8")
    if args.jira:
        task += f"\n\nJira key: {args.jira}\nThe selected AI agent should retrieve the Jira issue through an available Jira/MCP integration when possible."

    providers = config.get("providers", {})
    agent = args.agent or config.get("harness", {}).get("default_provider", "claude")
    if agent not in providers:
        print(f"Unknown provider: {agent}. Available: {', '.join(providers)}", file=sys.stderr)
        return 2
    provider = dict(providers[agent])
    provider["name"] = agent

    run_dir = make_run_dir()
    repo_map = build_repo_map()
    memory = relevant_memory(task, int(config.get("router", {}).get("memory_budget", 900)))
    route = heuristic_route(task)
    if config.get("harness", {}).get("auto_route", True) and not args.dry_run:
        route = route_task(provider, task, args.source, args.jira, memory, repo_map, run_dir, False)
    if args.workflow and args.workflow in config.get("workflows", {}):
        route["workflow"] = args.workflow
    phases = phase_sequence(route)

    manifest = {
        "version": 2,
        "created_at": now_iso(),
        "agent": agent,
        "source": args.source,
        "jira": args.jira,
        "task": task,
        "route": route,
        "phases": phases,
        "git_initial": git_state(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "repository-map.md").write_text(repo_map, encoding="utf-8")
    (run_dir / "task.txt").write_text(task, encoding="utf-8")

    history = ""
    context = compact(repo_map, int(config.get("router", {}).get("context_budget", 1400)))
    for phase in phases:
        if phase == "context":
            continue
        prompt = render_prompt(phase, task, args.source, args.jira, route, context, memory, compact(history, int(config.get("router", {}).get("max_history_chars", 5000))))
        prompt_file = run_dir / f"{phase}.prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        output_file = run_dir / f"{phase}.output.md"
        code, output = invoke(provider, prompt_file, phase, run_dir, output_file, args.dry_run)
        history += f"\n# {phase}\n{compact(output, 1800)}\n"
        if code != 0:
            return code
        if phase == "validate" and not validation(config, run_dir):
            (run_dir / "validation.failed").write_text("validation failed\n", encoding="utf-8")
            return 1

    manifest["completed_at"] = now_iso()
    manifest["git_final"] = git_state()
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if config.get("harness", {}).get("learn_after_run", True) and not args.dry_run:
        learn_from_run(run_dir, task, route)
        if config.get("harness", {}).get("auto_groom", True):
            groom(config)
    print(f"Run complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
