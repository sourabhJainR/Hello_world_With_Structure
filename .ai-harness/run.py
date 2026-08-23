#!/usr/bin/env python3
"""Adaptive provider-neutral AI coding harness."""
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
PRINCIPLES = HARNESS / "principles.md"
CAPABILITIES = ("research", "poc", "grill")


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
    return {word for word in words if word not in stop}


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
        words = normalize_words(" ".join(str(item.get(key, "")) for key in ("pattern", "lesson", "scope", "tags")))
        overlap = len(task_words & words)
        confidence = float(item.get("confidence", 0.5))
        score = overlap * 2 + confidence
        if overlap or confidence >= 0.9:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
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


def load_principles(limit: int = 7000) -> str:
    if not PRINCIPLES.exists():
        return "Use language-neutral engineering judgment focused on correctness, simplicity, maintainability, security, testing, compatibility, and evidence."
    return compact(PRINCIPLES.read_text(encoding="utf-8"), limit)


def applicable_principles(task: str, route: dict[str, Any]) -> list[str]:
    text = task.lower()
    selected = ["DRY", "YAGNI", "KISS", "DI / Dependency Inversion", "Separation of Concerns", "High Cohesion / Low Coupling", "Compatibility by Default", "Test the Behavior", "Evidence over Assumption", "Locality of Change"]
    if route.get("risk") in {"high", "critical"} or any(word in text for word in ("security", "auth", "permission", "secret")):
        selected += ["Security by Default", "Fail Fast and Explicitly", "Least Knowledge"]
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
    value["capabilities"] = list(dict.fromkeys([cap for cap in value.get("capabilities", []) if cap in CAPABILITIES]))
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
    values = {"{prompt_file}": str(prompt_file), "{workspace}": str(ROOT), "{phase}": phase, "{run_dir}": str(run_dir)}
    command = [values.get(value, value) for value in provider["command"]]
    working = provider.get("working_directory", "{workspace}")
    cwd = Path(values.get(working, working))
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
    principles = load_principles()
    selected = applicable_principles(task, route)
    return f"""# AI Coding Harness

You are operating inside an existing repository. The rules are language-neutral. Adapt them to the language, runtime, architecture, and conventions already present. Do not introduce framework-specific patterns merely to satisfy a principle name.

## Engineering principles

Applicable principles for this task: {', '.join(selected)}

{principles}

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
{history or 'none'}

## Phase rules
{phase_rules}

## Token discipline
Use the smallest amount of context needed. Prefer targeted file reads over broad dumps. Summarize completed work for the next phase. Never claim a command or source was used unless it was used.
"""


def route_task(provider: dict[str, Any], task: str, source: str, jira: str | None, memory: str, repo_map: str, run_dir: Path, dry_run: bool) -> dict[str, Any]:
    prompt = f"""Route this software-engineering request. Do not modify files. Keep the result language-neutral.

Return exactly one line starting with ROUTE_JSON: followed by JSON with:
mode: one of implement, debug, research, poc, review
capabilities: zero or more of research, poc, grill
risk: low, medium, high, critical
uncertainty: known, moderate, unknown
scope: file, component, service, repository, cross-repository
principles: array containing the principle names that materially constrain the task
reason: <= 300 characters

Apply these principles while routing: DRY, YAGNI, KISS, DI / Dependency Inversion, SOLID, separation of concerns, high cohesion / low coupling, composition over inheritance, least knowledge, fail fast, single source of truth, compatibility by default, behavior-focused testing, security by default, observability, failure awareness, reversibility, evidence over assumption, locality of change.

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
    _, output = invoke(provider, route_file, "route", run_dir, output_file, dry_run)
    parsed = parse_route_output(output)
    return parsed or heuristic_route(task)


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
                (run_dir / "validation.failed").write_text("failed\n", encoding="utf-8")
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
    lessons: list[str] = []
    for line in review.splitlines():
        clean = line.strip(" -#")
        if clean and any(word in clean.lower() for word in ("lesson", "recommend", "avoid", "prefer", "risk")):
            lessons.append(clean[:500])
    observation = {"id": hashlib.sha256(f"{task}|{now_iso()}".encode()).hexdigest()[:12], "created_at": now_iso(), "task": compact(task, 500), "route": route, "success": validation_ok, "lessons": lessons[:5]}
    append_jsonl(observations_path, observation)
    for lesson in lessons[:5]:
        append_jsonl(patterns_path, {"id": hashlib.sha256(lesson.encode()).hexdigest()[:12], "created_at": now_iso(), "pattern": lesson, "scope": route.get("scope", "repository"), "confidence": 0.6 if validation_ok else 0.3})


def groom_memory() -> None:
    patterns_path, _ = memory_paths()
    items = read_jsonl(patterns_path)
    latest: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item.get("id") or hashlib.sha256(str(item.get("pattern", "")).encode()).hexdigest()[:12])
        previous = latest.get(key)
        if previous is None or str(item.get("created_at", "")) > str(previous.get("created_at", "")):
            latest[key] = item
    promoted: list[dict[str, Any]] = []
    for item in latest.values():
        confidence = float(item.get("confidence", 0.0))
        item["confidence"] = min(0.99, confidence + 0.05) if confidence >= 0.6 else confidence
        if item["confidence"] >= 0.8:
            item["status"] = "trusted"
        promoted.append(item)
    promoted.sort(key=lambda x: (float(x.get("confidence", 0)), str(x.get("created_at", ""))), reverse=True)
    patterns_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in promoted[:500]), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptive language-neutral AI coding harness")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("providers")
    sub.add_parser("principles")
    sub.add_parser("memory")
    sub.add_parser("groom")
    context = sub.add_parser("context")
    context.add_argument("--output", default=".ai-harness/repository-map.md")

    run = sub.add_parser("run")
    run.add_argument("--agent", default="claude")
    run.add_argument("--task", required=True)
    run.add_argument("--jira")
    run.add_argument("--source", default="prompt")
    run.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    config = load_config()

    if args.action == "providers":
        print("\n".join(config.get("providers", {}).keys()))
        return 0
    if args.action == "principles":
        print(PRINCIPLES.read_text(encoding="utf-8"))
        return 0
    if args.action == "memory":
        patterns, observations = memory_paths()
        print(f"patterns: {patterns}")
        print(f"observations: {observations}")
        print(f"pattern_count: {len(read_jsonl(patterns))}")
        print(f"observation_count: {len(read_jsonl(observations))}")
        return 0
    if args.action == "groom":
        groom_memory()
        print("Memory groomed")
        return 0
    if args.action == "context":
        target = ROOT / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_repo_map(), encoding="utf-8")
        print(target)
        return 0

    providers = config.get("providers", {})
    if args.agent not in providers:
        print(f"Unknown agent: {args.agent}. Configured: {', '.join(providers)}", file=sys.stderr)
        return 2
    provider = dict(providers[args.agent])
    provider["name"] = args.agent
    run_dir = make_run_dir()
    repo_map = build_repo_map()
    task_memory = relevant_memory(args.task, int(config.get("tokens", {}).get("memory", 1200)))
    route = route_task(provider, args.task, args.source, args.jira, task_memory, repo_map, run_dir, args.dry_run)
    phases = phase_sequence(route)
    metadata = {"agent": args.agent, "source": args.source, "jira": args.jira, "task": args.task, "route": route, "phases": phases, "started_at": now_iso()}
    (run_dir / "manifest.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "repository-map.md").write_text(repo_map, encoding="utf-8")
    (run_dir / "task.txt").write_text(args.task, encoding="utf-8")
    history = ""
    for phase in phases:
        if phase == "context":
            continue
        prompt_file = run_dir / f"{phase}.prompt.md"
        output_file = run_dir / f"{phase}.output.md"
        prompt_file.write_text(render_prompt(phase, args.task, args.source, args.jira, route, repo_map, task_memory, history), encoding="utf-8")
        code, output = invoke(provider, prompt_file, phase, run_dir, output_file, args.dry_run)
        if code != 0:
            print(f"phase failed: {phase}", file=sys.stderr)
            return code
        if phase == "validate" and not args.dry_run and not validation(config, run_dir):
            print("validation failed", file=sys.stderr)
            return 1
        if phase == "learn" and not args.dry_run:
            learn_from_run(run_dir, args.task, route)
        history = compact(output, int(config.get("tokens", {}).get("phase_history", 1800)))
    metadata["completed_at"] = now_iso()
    metadata["principles"] = applicable_principles(args.task, route)
    (run_dir / "manifest.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())