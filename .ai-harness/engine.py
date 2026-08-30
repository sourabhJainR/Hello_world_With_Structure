#!/usr/bin/env python3
"""Single-run, adaptive, provider-neutral AI coding coordinator."""
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
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

from observability import ConfigurationError, HarnessError, configure_logging, emit_event, exception_summary

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


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def load_config() -> dict[str, Any]:
    try:
        with CONFIG_PATH.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Unable to load {CONFIG_PATH}: {exc}") from exc


def ensure_dirs() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    MEMORY.mkdir(parents=True, exist_ok=True)


def compact(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    head = max(1, int(limit * 0.72))
    tail = max(1, limit - head - 60)
    return text[:head] + "\n... [compacted] ...\n" + text[-tail:]


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp = Path(handle.name)
    temp.replace(path)


def write_json_atomic(path: Path, value: object) -> None:
    write_text_atomic(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


def run_capture(command: list[str], cwd: Path = ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT: {exc}"
    except OSError as exc:
        return 127, f"ERROR: {exc}"
    return result.returncode, (result.stdout or result.stderr).strip()


def git_state() -> str:
    parts = []
    for command in (["git", "status", "--short"], ["git", "branch", "--show-current"], ["git", "rev-parse", "HEAD"]):
        code, output = run_capture(command)
        parts.append(f"$ {shlex.join(command)}\n{output if code == 0 else 'ERROR: ' + output}")
    return "\n".join(parts)


def diff_summary() -> str:
    parts = []
    for command in (["git", "diff", "--stat"], ["git", "diff", "--check"], ["git", "diff", "--name-only"]):
        _, output = run_capture(command)
        parts.append(f"$ {shlex.join(command)}\n{output}")
    return "\n".join(parts)


def diff_check() -> tuple[bool, str]:
    code, output = run_capture(["git", "diff", "--check"])
    return code == 0, output


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


def repository_map(limit: int = 500) -> str:
    code, output = run_capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"], timeout=30)
    if code != 0:
        return "# Repository Map\nUnavailable: git ls-files failed."
    files = [line for line in output.splitlines() if line][:limit]
    return "# Repository Map\n\n" + "\n".join(f"- {name}" for name in files)


def profile_repository() -> dict[str, Any]:
    script = HARNESS / "project_profile.py"
    if not script.exists():
        return {}
    code, output = run_capture([sys.executable, str(script)], timeout=30)
    if code != 0:
        return {"profile_error": compact(output, 500)}
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return {"profile_error": "project_profile.py returned invalid JSON"}
    return value if isinstance(value, dict) else {}


def normalize_words(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "have", "will", "task", "change", "please", "need", "make", "using"}
    return {word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()) if word not in stop}


def relevant_memory(task: str, budget: int = 900) -> str:
    items = read_jsonl(MEMORY / "patterns.jsonl") + read_jsonl(MEMORY / "observations.jsonl")
    words = normalize_words(task)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        if item.get("status") not in (None, "trusted", "candidate"):
            continue
        text = " ".join(str(item.get(key, "")) for key in ("pattern", "lesson", "scope", "task", "tags"))
        overlap = len(words & normalize_words(text))
        confidence = float(item.get("confidence", 0.5))
        if overlap or confidence >= 0.9:
            ranked.append((overlap * 2 + confidence, item))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[str] = []
    used = 0
    for _, item in ranked[:12]:
        encoded = json.dumps(item, ensure_ascii=False)
        if used + len(encoded) > budget:
            break
        selected.append(encoded)
        used += len(encoded)
    return "\n".join(selected) or "No relevant learned patterns."


def load_principles(limit: int = 7000) -> str:
    if not PRINCIPLES.exists():
        return "Use language-neutral engineering judgment focused on correctness, simplicity, maintainability, security, compatibility, testing, failure awareness and evidence."
    return compact(PRINCIPLES.read_text(encoding="utf-8"), limit)


def heuristic_route(task: str) -> dict[str, Any]:
    text = task.lower()
    mode = "implement"
    risk = "low"
    uncertainty = "known"
    capabilities: list[str] = []

    if any(token in text for token in ("poc", "proof of concept", "feasibility", "spike", "prototype", "experiment")):
        mode = "poc"; capabilities.append("poc"); uncertainty = "unknown"
    elif any(token in text for token in ("review", "assess", "audit")):
        mode = "review"
    elif any(token in text for token in ("research", "investigate options", "which library", "which framework", "latest")):
        mode = "research"; capabilities.append("research"); uncertainty = "moderate"
    elif any(token in text for token in ("why", "diagnose", "intermittent", "root cause", "failing", "hang", "error", "regression", "broken")):
        mode = "debug"; uncertainty = "moderate"

    if mode == "implement" and any(token in text for token in ("ambiguous", "unclear requirements", "clarify requirements", "not enough requirements", "undefined behavior")):
        mode = "grill"; capabilities.append("grill")

    if mode not in ("research", "poc") and any(token in text for token in ("compare", "evaluate", "unknown", "architecture")):
        capabilities.append("research"); uncertainty = "moderate"

    if any(token in text for token in ("security", "authentication", "authorization", "production", "migration", "breaking", "performance", "scale", "release")):
        capabilities.append("grill"); risk = "high"

    return {"mode": mode, "capabilities": list(dict.fromkeys(capabilities)), "risk": risk, "uncertainty": uncertainty, "scope": "repository", "reason": "deterministic heuristic", "confidence": 0.75}

def normalize_route(value: dict[str, Any]) -> dict[str, Any]:
    route = dict(value)
    route["mode"] = route.get("mode") if route.get("mode") in MODES else "implement"
    route["risk"] = route.get("risk") if route.get("risk") in RISKS else "low"
    route["uncertainty"] = route.get("uncertainty") if route.get("uncertainty") in UNCERTAINTIES else "known"
    route["capabilities"] = list(dict.fromkeys(c for c in route.get("capabilities", []) if c in CAPABILITIES))
    route["scope"] = str(route.get("scope", "repository"))
    route["confidence"] = max(0.0, min(1.0, float(route.get("confidence", 0.5))))
    route["reason"] = compact(str(route.get("reason", "")), 300)
    return route


def parse_route(output: str) -> dict[str, Any] | None:
    for line in output.splitlines():
        if "ROUTE_JSON:" not in line:
            continue
        try:
            value = json.loads(line.split("ROUTE_JSON:", 1)[1].strip())
        except json.JSONDecodeError:
            return None
        return normalize_route(value) if isinstance(value, dict) else None
    return None


def provider_command(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path) -> tuple[list[str], Path]:
    replacements = {
        "{prompt_file}": str(prompt_file),
        "{workspace}": str(ROOT),
        "{phase}": phase,
        "{run_dir}": str(run_dir),
        "{python}": sys.executable,
    }
    command = [replacements.get(value, value) for value in provider["command"]]
    working = replacements.get(provider.get("working_directory", "{workspace}"), provider.get("working_directory", str(ROOT)))
    return command, Path(working)


def invoke(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path, timeout: int, dry_run: bool, logger) -> tuple[int, str, float]:
    command, cwd = provider_command(provider, prompt_file, phase, run_dir)
    output_file = run_dir / f"{phase}.output.md"
    started = time.monotonic()
    emit_event(run_dir, "provider.start", phase=phase, provider=provider.get("name"))
    if dry_run:
        output = "DRY RUN\n$ " + shlex.join(command)
        write_text_atomic(output_file, output + "\n")
        return 0, output, 0.0
    try:
        result = subprocess.run(command, cwd=cwd, env=os.environ.copy(), text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output = f"TIMEOUT after {timeout}s\n{exc}"
        code = 124
    except OSError as exc:
        output = f"ERROR: {exc}"
        code = 127
    else:
        output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        code = result.returncode
    write_text_atomic(output_file, output)
    duration = time.monotonic() - started
    emit_event(run_dir, "provider.finish", phase=phase, provider=provider.get("name"), exit_code=code, duration_seconds=round(duration, 3))
    if code == 0:
        logger.info("phase=%s provider=%s completed", phase, provider.get("name"))
    else:
        logger.error("phase=%s provider=%s failed exit=%s", phase, provider.get("name"), code)
    return code, output, duration


def build_prompt(phase: str, task: str, source: str, jira: str | None, route: dict[str, Any], repo_map: str, memory: str, profile: dict[str, Any], history: str) -> str:
    phase_path = PROMPTS / f"{phase}.md"
    phase_rules = phase_path.read_text(encoding="utf-8") if phase_path.exists() else ""
    return f"""# AI Coding Harness\n\nOperate inside the existing repository. Reuse repository conventions before introducing new infrastructure or organization.\n\n## Task\nSource: {source}\nJira: {jira or 'none'}\n{task}\n\n## Route\n{json.dumps(route, indent=2)}\n\n## Repository profile\n{json.dumps(profile, indent=2)}\n\n## Learned evidence\n{memory}\n\n## Repository map\n{repo_map}\n\n## Prior evidence\n{compact(history or 'none', 4500)}\n\n## Engineering principles\n{load_principles()}\n\n## Phase instructions\n{phase_rules}\n\n## Non-negotiable rules\n- Inspect before changing.\n- Follow local naming, placement, segregation, exception, logging, telemetry, dependency and test conventions.\n- When multiple compatible patterns exist, use the most mature local pattern that fits the responsibility.\n- Do not create generic shared/common/utils locations without strong repository evidence.\n- Do not claim verification without evidence.\n- Every retry must add evidence or materially change the approach.\n- Stay within task scope and keep changes reversible where practical.\n"""


def route_with_provider(provider: dict[str, Any], task: str, source: str, jira: str | None, repo_map: str, memory: str, run_dir: Path, config: dict[str, Any], dry_run: bool, logger) -> dict[str, Any]:
    prompt = f"""Route this engineering task without changing files. Return exactly one line beginning with ROUTE_JSON: followed by JSON containing mode, capabilities, risk, uncertainty, scope, reason, confidence. Use the minimum safe route.\n\nTask source: {source}\nJira: {jira or 'none'}\nTask: {task}\n\nRepository map:\n{compact(repo_map, int(config['router']['context_budget']))}\n\nRelevant memory:\n{compact(memory, int(config['router']['memory_budget']))}\n"""
    prompt_file = run_dir / "route.prompt.md"
    write_text_atomic(prompt_file, prompt)
    code, output, duration = invoke(provider, prompt_file, "route", run_dir, int(config["execution"]["provider_timeout_seconds"]), dry_run, logger)
    route = parse_route(output) if code == 0 else None
    if route is None:
        route = heuristic_route(task)
    route["router_duration_seconds"] = round(duration, 3)
    route["router_source"] = "provider" if code == 0 and parse_route(output) else "heuristic"
    return route


def phases_for(route: dict[str, Any], workflow: str | None, config: dict[str, Any]) -> list[str]:
    if workflow:
        workflows = config.get("workflows", {})
        selected = workflows.get(workflow)
        if not isinstance(selected, dict) or not isinstance(selected.get("phases"), list):
            raise ConfigurationError(f"Unknown workflow: {workflow}")
        return [str(p) for p in selected["phases"]]
    phases = ["context"]
    mode = route["mode"]
    caps = set(route["capabilities"])
    if "research" in caps or mode == "research":
        phases.append("research")
    if "poc" in caps or mode == "poc":
        phases.append("poc")
    if mode == "debug":
        phases.append("debug")
    if mode in {"implement", "debug"}:
        phases.extend(["execute", "validate"])
    elif mode == "review":
        phases.append("review")
    if "grill" in caps:
        phases.append("grill")
    if mode in {"implement", "debug", "poc"}:
        phases.append("review")
    phases.append("learn")
    return list(dict.fromkeys(phases))


def run_validation(config: dict[str, Any], run_dir: Path) -> tuple[bool, list[dict[str, Any]]]:
    commands: list[list[str]] = []
    for item in config.get("validation", {}).get("commands", []):
        if isinstance(item, list) and all(isinstance(part, str) for part in item):
            commands.append(item)
        elif isinstance(item, str):
            commands.append(shlex.split(item, posix=os.name != "nt"))
    if not commands and config.get("validation", {}).get("auto_discover", False):
        if (ROOT / "package.json").exists():
            commands.append(["npm", "test", "--if-present"])
        if (ROOT / "go.mod").exists():
            commands.append(["go", "test", "./..."])
        if (ROOT / "Cargo.toml").exists():
            commands.append(["cargo", "test"])
        if list(ROOT.glob("*.sln")) or list(ROOT.glob("*.csproj")):
            commands.append(["dotnet", "test", "--nologo"])
        if (ROOT / "pyproject.toml").exists() or (ROOT / "pytest.ini").exists():
            if list(ROOT.rglob("test_*.py")) or list(ROOT.rglob("*_test.py")):
                commands.append([sys.executable, "-m", "pytest", "-q"])
    if not commands:
        return True, []
    results: list[dict[str, Any]] = []
    log = run_dir / "validation.log"
    with log.open("w", encoding="utf-8") as stream:
        for command in commands[:5]:
            stream.write(f"$ {shlex.join(command)}\n")
            start = time.monotonic()
            try:
                result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, text=True, check=False, timeout=int(config["execution"]["validation_timeout_seconds"]))
                code = result.returncode
                status = "passed" if code == 0 else "failed"
            except subprocess.TimeoutExpired:
                code = 124
                status = "timeout"
            results.append({"command": command, "status": status, "exit_code": code, "duration_seconds": round(time.monotonic() - start, 3)})
            if code != 0:
                return False, results
    return True, results


def review_requires_fix(output: str) -> bool:
    if "HARNESS_FIX_REQUIRED" in output:
        return True
    return re.search(r"^APPROVAL:\s*(?:REJECT|CHANGES_REQUIRED)\s*$", output, re.IGNORECASE | re.MULTILINE) is not None


def save_checkpoint(run_dir: Path, manifest: dict[str, Any], phase: str, status: str, next_phase: str | None) -> None:
    write_json_atomic(run_dir / "checkpoint.json", {"run_id": manifest["run_id"], "updated_at": now_iso(), "phase": phase, "status": status, "next_phase": next_phase, "completed_phases": manifest.get("completed_phases", [])})


def learn(run_dir: Path, task: str, route: dict[str, Any], manifest: dict[str, Any]) -> None:
    review_path = run_dir / "review.output.md"
    review = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    validation_ok = bool(manifest.get("validation", {}).get("passed", True))
    lessons = []
    for line in review.splitlines():
        clean = line.strip(" -#")
        if clean and any(word in clean.lower() for word in ("lesson", "recommend", "avoid", "prefer", "root cause")):
            lessons.append(compact(clean, 500))
    append_jsonl(MEMORY / "observations.jsonl", {"id": hashlib.sha256(f"{task}|{manifest['run_id']}".encode()).hexdigest()[:12], "created_at": now_iso(), "task": compact(task, 500), "route": route, "provider": manifest.get("provider"), "validation_passed": validation_ok, "retries": manifest.get("retries", 0), "lessons": lessons[:5]})
    for lesson_text in lessons[:5]:
        append_jsonl(MEMORY / "patterns.jsonl", {"id": hashlib.sha256(lesson_text.encode()).hexdigest()[:12], "created_at": now_iso(), "pattern": lesson_text, "scope": route.get("scope", "repository"), "confidence": 0.6 if validation_ok else 0.35, "status": "candidate", "success": validation_ok})


def groom_memory(config: dict[str, Any]) -> dict[str, Any]:
    patterns_path = MEMORY / "patterns.jsonl"
    observations = read_jsonl(MEMORY / "observations.jsonl")
    patterns = read_jsonl(patterns_path)
    min_obs = int(config["learning"]["min_observations_for_promotion"])
    floor = float(config["learning"]["min_success_rate_for_promotion"])
    max_items = int(config["learning"]["max_memory_items"])
    outcomes: dict[str, list[bool]] = {}
    for observation in observations:
        for lesson_text in observation.get("lessons", []):
            outcomes.setdefault(str(lesson_text), []).append(bool(observation.get("validation_passed", False)))
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in patterns:
        key = str(item.get("pattern", "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        history = outcomes.get(key, [])
        updated = dict(item)
        if len(history) >= min_obs:
            success_rate = sum(history) / len(history)
            updated["observations"] = len(history)
            updated["success_rate"] = round(success_rate, 3)
            updated["status"] = "trusted" if success_rate >= floor else "candidate"
            updated["confidence"] = round(max(float(item.get("confidence", 0.5)), success_rate), 3)
        chosen.append(updated)
        if len(chosen) >= max_items:
            break
    write_text_atomic(patterns_path, "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in chosen))
    trusted = sum(1 for item in chosen if item.get("status") == "trusted")
    return {"patterns": len(chosen), "trusted": trusted}


def evaluate() -> dict[str, Any]:
    cases = read_jsonl(EVALS)
    results = []
    for case in cases:
        route = heuristic_route(str(case.get("task") or case.get("prompt") or ""))
        expected_mode = case.get("expected_mode")
        required = set(case.get("capabilities", case.get("must_include", [])))
        actual = set(route.get("capabilities", []))
        results.append({"id": case.get("id"), "passed": route["mode"] == expected_mode and required.issubset(actual), "expected_mode": expected_mode, "observed_mode": route["mode"], "expected_capabilities": sorted(required), "observed_capabilities": sorted(actual)})
    passed = sum(1 for item in results if item["passed"])
    return {"cases": len(results), "passed": passed, "failed": len(results) - passed, "results": results}


def run_task(args: argparse.Namespace, config: dict[str, Any], logger) -> int:
    providers = config.get("providers", {})
    provider_name = args.agent or config.get("harness", {}).get("default_provider")
    if provider_name not in providers:
        raise ConfigurationError(f"Unknown provider: {provider_name}")
    provider = dict(providers[provider_name])
    provider["name"] = provider_name

    if args.resume:
        run_dir = Path(args.resume).resolve()
        manifest_path = run_dir / "manifest.json"
        checkpoint_path = run_dir / "checkpoint.json"
        if not manifest_path.exists() or not checkpoint_path.exists():
            raise ConfigurationError("Resume requires a valid run directory with manifest.json and checkpoint.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        task = str(manifest["task"])
        route = normalize_route(manifest["route"])
        source = str(manifest.get("source", "resume"))
        jira = manifest.get("jira")
        repo_map = (run_dir / "repository-map.md").read_text(encoding="utf-8") if (run_dir / "repository-map.md").exists() else repository_map()
        profile = manifest.get("repository_profile", {})
        phases = list(manifest.get("phases", []))
        next_phase = checkpoint.get("next_phase")
        if next_phase in phases:
            phases = phases[phases.index(next_phase):]
        elif checkpoint.get("status") == "completed":
            return 0
        else:
            raise ConfigurationError("Checkpoint does not identify a resumable phase")
    else:
        run_dir = make_run_dir()
        task = args.task.strip()
        source = "prompt"
        jira = args.jira
        if args.jira_file:
            jira_path = Path(args.jira_file)
            if not jira_path.is_file():
                raise ConfigurationError(f"Jira file not found: {jira_path}")
            task = (task + "\n\nJira context:\n" + jira_path.read_text(encoding="utf-8")).strip()
            source = "jira-file"
        elif args.jira:
            source = "jira"
            task = task or f"Work on Jira item {args.jira}"
        if not task:
            raise ConfigurationError("A task, Jira key, or Jira file is required")
        repo_map = repository_map()
        profile = profile_repository()
        memory = relevant_memory(task, int(config["router"]["memory_budget"]))
        route = route_with_provider(provider, task, source, jira, repo_map, memory, run_dir, config, args.dry_run, logger)
        phases = phases_for(route, args.workflow, config)
        manifest = {
            "version": 5,
            "run_id": run_dir.name,
            "started_at": now_iso(),
            "provider": provider_name,
            "task": task,
            "source": source,
            "jira": jira,
            "workflow": args.workflow or "adaptive",
            "route": route,
            "phases": phases,
            "completed_phases": [],
            "retries": 0,
            "repository_profile": profile,
            "initial_git": git_state(),
        }
        write_json_atomic(run_dir / "manifest.json", manifest)
        write_text_atomic(run_dir / "task.txt", task)
        write_text_atomic(run_dir / "repository-map.md", repo_map)
        save_checkpoint(run_dir, manifest, "route", "completed", phases[0] if phases else None)

    history: list[str] = []
    if not phases:
        return 0
    phase_timeout = int(config["execution"]["phase_timeout_seconds"])
    validation_needed = False

    for index, phase in enumerate(phases):
        next_phase = phases[index + 1] if index + 1 < len(phases) else None
        emit_event(run_dir, "phase.start", phase=phase)
        if phase == "context":
            manifest.setdefault("completed_phases", []).append(phase)
            save_checkpoint(run_dir, manifest, phase, "completed", next_phase)
            continue
        if phase == "validate":
            validation_needed = True
            passed, results = run_validation(config, run_dir)
            manifest["validation"] = {"passed": passed, "results": results}
            write_json_atomic(run_dir / "manifest.json", manifest)
            if not passed:
                if not repair_after_failure(config, provider, run_dir, manifest, task, source, jira, route, history, args.dry_run, logger):
                    manifest["status"] = "blocked_by_validation"
                    write_json_atomic(run_dir / "manifest.json", manifest)
                    save_checkpoint(run_dir, manifest, phase, "blocked", "repair")
                    return 1
            manifest.setdefault("completed_phases", []).append(phase)
            save_checkpoint(run_dir, manifest, phase, "completed", next_phase)
            continue
        if phase == "learn":
            learn(run_dir, task, route, manifest)
            manifest.setdefault("completed_phases", []).append(phase)
            write_json_atomic(run_dir / "manifest.json", manifest)
            save_checkpoint(run_dir, manifest, phase, "completed", next_phase)
            continue

        prompt_file = run_dir / f"{phase}.prompt.md"
        memory = relevant_memory(task, int(config["router"]["memory_budget"]))
        context = (run_dir / "repository-map.md").read_text(encoding="utf-8")
        prompt = build_prompt(phase, task, source, jira, route, context, memory, profile, "\n\n".join(history))
        write_text_atomic(prompt_file, prompt)
        succeeded = False
        max_attempts = int(config["execution"]["max_phase_retries"]) + 1
        for attempt in range(max_attempts):
            if attempt:
                manifest["retries"] += 1
                prompt = build_prompt(phase, task, source, jira, route, context, memory, profile, "\n\n".join(history) + "\nPrevious attempt failed. Gather new evidence and change the approach.")
                write_text_atomic(prompt_file, prompt)
            code, output, duration = invoke(provider, prompt_file, phase, run_dir, phase_timeout, args.dry_run, logger)
            history.append(compact(f"[{phase}] {output}", 2500))
            manifest.setdefault("phase_metrics", {})[phase] = {"attempt": attempt, "exit_code": code, "duration_seconds": round(duration, 3)}
            if code == 0:
                succeeded = True
                break
        if not succeeded:
            manifest["status"] = "failed"
            write_json_atomic(run_dir / "manifest.json", manifest)
            save_checkpoint(run_dir, manifest, phase, "failed", phase)
            return 1
        if phase == "review" and review_requires_fix(output):
            if not repair_after_failure(config, provider, run_dir, manifest, task, source, jira, route, history, args.dry_run, logger):
                manifest["status"] = "blocked_by_review"
                write_json_atomic(run_dir / "manifest.json", manifest)
                save_checkpoint(run_dir, manifest, phase, "blocked", "repair")
                return 1
        if phase in {"execute", "debug", "poc", "research", "grill", "review"}:
            manifest.setdefault("git_evidence", {})[phase] = diff_summary()
        manifest.setdefault("completed_phases", []).append(phase)
        write_json_atomic(run_dir / "manifest.json", manifest)
        save_checkpoint(run_dir, manifest, phase, "completed", next_phase)

    passed_diff, diff_output = diff_check()
    manifest["verification"] = {"validation_passed": manifest.get("validation", {}).get("passed", True), "diff_check_passed": passed_diff, "diff_check": diff_output}
    manifest["git_final"] = git_state()
    manifest["git_diff"] = diff_summary()
    manifest["completed_at"] = now_iso()
    manifest["status"] = "completed" if manifest["verification"]["validation_passed"] and passed_diff else "blocked_by_verification"
    write_json_atomic(run_dir / "manifest.json", manifest)
    save_checkpoint(run_dir, manifest, "complete", manifest["status"], None)
    emit_event(run_dir, "run.finish", status=manifest["status"])
    return 0 if manifest["status"] == "completed" else 1


def repair_after_failure(config: dict[str, Any], provider: dict[str, Any], run_dir: Path, manifest: dict[str, Any], task: str, source: str, jira: str | None, route: dict[str, Any], history: list[str], dry_run: bool, logger) -> bool:
    limit = int(config["execution"]["max_repair_attempts"])
    context = (run_dir / "repository-map.md").read_text(encoding="utf-8")
    for attempt in range(1, limit + 1):
        manifest["retries"] += 1
        prompt_file = run_dir / f"repair-{attempt}.prompt.md"
        prompt = build_prompt("repair", task, source, jira, route, context, relevant_memory(task, 700), {}, "\n\n".join(history) + "\nVerification failed. Diagnose before changing code.")
        write_text_atomic(prompt_file, prompt)
        code, output, duration = invoke(provider, prompt_file, "repair", run_dir, int(config["execution"]["phase_timeout_seconds"]), dry_run, logger)
        history.append(compact(f"[repair-{attempt}] {output}", 2500))
        manifest.setdefault("phase_metrics", {})[f"repair-{attempt}"] = {"exit_code": code, "duration_seconds": round(duration, 3)}
        if code != 0:
            continue
        passed, results = run_validation(config, run_dir)
        manifest["validation"] = {"passed": passed, "results": results}
        if passed:
            return True
    return False


def command_line() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Adaptive provider-neutral AI coding harness")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("providers", "capabilities", "context", "memory", "groom", "eval"):
        sub.add_parser(name)
    run = sub.add_parser("run")
    run.add_argument("--task", default="")
    run.add_argument("--jira")
    run.add_argument("--jira-file")
    run.add_argument("--agent")
    run.add_argument("--workflow")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--resume")
    return parser


def main() -> int:
    parser = command_line()
    args = parser.parse_args()
    config = load_config()
    logger = configure_logging(None, str(config.get("observability", {}).get("log_level", "INFO")))
    run_dir: Path | None = None
    try:
        if args.action == "providers":
            print("\n".join(config.get("providers", {}).keys()))
            return 0
        if args.action == "capabilities":
            print("\n".join(CAPABILITIES))
            return 0
        if args.action == "context":
            target = HARNESS / "repository-map.md"
            write_text_atomic(target, repository_map())
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
            print(json.dumps(evaluate(), indent=2))
            return 0
        if args.resume:
            run_dir = Path(args.resume).resolve()
            logger = configure_logging(run_dir, str(config.get("observability", {}).get("log_level", "INFO")))
            return run_task(args, config, logger)
        run_dir = make_run_dir()
        logger = configure_logging(run_dir, str(config.get("observability", {}).get("log_level", "INFO")))
        emit_event(run_dir, "run.start", provider=args.agent, workflow=args.workflow)
        return run_task(args, config, logger)
    except HarnessError as exc:
        if run_dir:
            emit_event(run_dir, "run.error", **exception_summary(exc))
        logger.error("harness error: %s", exc)
        return 2
    except Exception as exc:
        if run_dir:
            emit_event(run_dir, "run.crash", **exception_summary(exc))
        logger.exception("unhandled harness failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
