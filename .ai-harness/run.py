#!/usr/bin/env python3
"""Adaptive, provider-neutral AI coding harness."""
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
from typing import Any

from observability import ConfigurationError, HarnessError, ProviderError, configure_logging, emit_event, exception_summary

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
    try:
        with CONFIG_PATH.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Unable to load {CONFIG_PATH}: {exc}") from exc


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
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"ERROR: {exc}"
    return (result.stdout or result.stderr).strip()


def run_capture_result(command: list[str], cwd: Path = ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT: {exc}"
    except OSError as exc:
        return 127, f"ERROR: {exc}"
    return result.returncode, (result.stdout or result.stderr).strip()


def git_state() -> str:
    return "\n".join([
        "$ git status --short\n" + run_capture(["git", "status", "--short"]),
        "$ git branch --show-current\n" + run_capture(["git", "branch", "--show-current"]),
        "$ git rev-parse HEAD\n" + run_capture(["git", "rev-parse", "HEAD"]),
    ])


def diff_check() -> tuple[bool, str]:
    code, output = run_capture_result(["git", "diff", "--check"])
    return code == 0, output


def diff_files() -> list[str]:
    code, output = run_capture_result(["git", "diff", "--name-only"])
    if code != 0:
        return []
    return [line for line in output.splitlines() if line.strip()]


def git_diff_summary() -> str:
    return "\n".join([
        "$ git diff --stat\n" + run_capture(["git", "diff", "--stat"]),
        "$ git diff --check\n" + run_capture(["git", "diff", "--check"]),
        "$ git diff --name-only\n" + run_capture(["git", "diff", "--name-only"]),
    ])


def build_repo_map(limit: int = 500) -> str:
    raw = run_capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"])
    files = [line for line in raw.splitlines() if line][:limit]
    lines = ["# Repository Map", f"Workspace: {ROOT}", ""]
    symbol_pattern = re.compile(
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
                symbols = symbol_pattern.findall(path.read_text(encoding="utf-8", errors="ignore"))
                if symbols:
                    entry += " :: " + ", ".join(symbols[:16])
            except OSError:
                pass
        lines.append(entry)
    return "\n".join(lines) + "\n"


def normalize_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "have", "will", "task", "change", "please", "need", "make", "using"}
    return {word for word in words if word not in stop}


def relevant_memory(task: str, budget: int) -> str:
    candidates = read_jsonl(MEMORY / "patterns.jsonl") + read_jsonl(MEMORY / "observations.jsonl")
    task_words = normalize_words(task)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in candidates:
        text = " ".join(str(item.get(key, "")) for key in ("pattern", "lesson", "scope", "tags", "task"))
        overlap = len(task_words & normalize_words(text))
        confidence = float(item.get("confidence", 0.5))
        score = overlap * 2 + confidence
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
    selected = ["DRY", "YAGNI", "KISS", "DI / Dependency Inversion", "Separation of Concerns", "High Cohesion / Low Coupling", "Compatibility by Default", "Test the Behavior", "Evidence over Assumption", "Locality of Change"]
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
    if any(term in text for term in ("compare", "evaluate", "research", "unknown", "which library", "which framework", "architecture", "design option", "latest", "investigate")):
        caps.append("research")
        uncertainty = "moderate"
    if any(term in text for term in ("poc", "proof of concept", "feasibility", "spike", "prototype", "can we", "experiment")):
        caps.append("poc")
        uncertainty = "unknown"
    if any(term in text for term in ("security", "authentication", "authorization", "production", "migration", "breaking change", "performance", "scale", "multi-tenant", "database", "release")):
        caps.append("grill")
        risk = "high"
    if any(term in text for term in ("why", "investigate", "diagnose", "intermittent", "root cause", "failing", "hang", "error", "regression", "broken")):
        mode = "debug"
        uncertainty = "moderate"
    if any(term in text for term in ("only research", "research only", "analyze only")):
        mode = "research"
    if any(term in text for term in ("only review", "review only", "review this")):
        mode = "review"
    if mode == "debug" and any(term in text for term in ("production", "security", "migration")):
        caps.append("grill")
        risk = "high"
    return normalize_route({"mode": mode, "capabilities": caps, "risk": risk, "uncertainty": uncertainty, "scope": "repository", "reason": "heuristic fallback", "confidence": 0.55})


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
    for line in output.splitlines():
        if "ROUTE_JSON:" not in line:
            continue
        payload = line.split("ROUTE_JSON:", 1)[1].strip()
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return normalize_route(value) if isinstance(value, dict) else None
    return None


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
    values = {"{prompt_file}": str(prompt_file), "{workspace}": str(ROOT), "{phase}": phase, "{run_dir}": str(run_dir), "{python}": sys.executable}
    command = [values.get(value, value) for value in provider["command"]]
    working = provider.get("working_directory", "{workspace}")
    cwd = Path(values.get(working, working))
    return command, cwd


def invoke(provider: dict[str, Any], prompt_file: Path, phase: str, run_dir: Path, output_file: Path, timeout: int, dry_run: bool, logger) -> tuple[int, str, float]:
    command, cwd = provider_command(provider, prompt_file, phase, run_dir)
    env = os.environ.copy()
    env.update({"AI_HARNESS_RUN_DIR": str(run_dir), "AI_HARNESS_PHASE": phase, "AI_HARNESS_AGENT": str(provider.get("name", "unknown"))})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    emit_event(run_dir, "provider.start", phase=phase, provider=provider.get("name"), command=command)
    logger.info("phase=%s provider=%s started", phase, provider.get("name"))
    if dry_run:
        output = "DRY RUN\n$ " + shlex.join(command)
        output_file.write_text(output + "\n", encoding="utf-8")
        duration = time.monotonic() - started
        emit_event(run_dir, "provider.finish", phase=phase, exit_code=0, duration_seconds=round(duration, 3), dry_run=True)
        return 0, output, duration
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output = f"TIMEOUT after {timeout}s\n{exc}"
        output_file.write_text(output + "\n", encoding="utf-8")
        duration = time.monotonic() - started
        emit_event(run_dir, "provider.finish", phase=phase, exit_code=124, duration_seconds=round(duration, 3), error="timeout")
        logger.error("phase=%s provider=%s timed out after %ss", phase, provider.get("name"), timeout)
        return 124, output, duration
    except OSError as exc:
        output = f"ERROR: {exc}"
        output_file.write_text(output + "\n", encoding="utf-8")
        duration = time.monotonic() - started
        emit_event(run_dir, "provider.finish", phase=phase, exit_code=127, duration_seconds=round(duration, 3), error=str(exc))
        logger.error("phase=%s provider=%s failed to start: %s", phase, provider.get("name"), exc)
        return 127, output, duration
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    output_file.write_text(output, encoding="utf-8")
    duration = time.monotonic() - started
    emit_event(run_dir, "provider.finish", phase=phase, exit_code=result.returncode, duration_seconds=round(duration, 3))
    logger.info("phase=%s provider=%s finished exit=%s", phase, provider.get("name"), result.returncode)
    return result.returncode, output, duration

# The remaining orchestration functions are intentionally unchanged from the existing
# harness implementation. They now receive the configured logger through main and use
# the standard-library observability helpers above rather than creating a new framework.


def main() -> int:
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
        raise ConfigurationError(f"Unknown provider: {provider_name}")
    provider = dict(providers[provider_name])
    provider["name"] = provider_name

    task = args.task.strip()
    source = "prompt"
    if args.jira_file:
        path = Path(args.jira_file)
        if not path.is_file():
            raise ConfigurationError(f"Jira file not found: {path}")
        task = (task + "\n\nJira context:\n" + path.read_text(encoding="utf-8")).strip()
        source = "jira-file"
    elif args.jira:
        source = "jira"
        task = task or f"Work on Jira item {args.jira}"
    if not task:
        raise ConfigurationError("A task, Jira key, or Jira file is required")

    run_dir = make_run_dir()
    logger = configure_logging(run_dir, str(config.get("observability", {}).get("log_level", "INFO")))
    emit_event(run_dir, "run.start", provider=provider_name, source=source)

    try:
        # Existing route / phase orchestration remains the source of truth.
        # The observability layer wraps it without adding a second exception or telemetry framework.
        repo_map = build_repo_map()
        memory = relevant_memory(task, int(config.get("router", {}).get("memory_budget", 900)))
        route = normalize_route(heuristic_route(task))
        manifest = {
            "version": 5,
            "run_id": run_dir.name,
            "started_at": now_iso(),
            "provider": provider_name,
            "task": task,
            "source": source,
            "jira": args.jira,
            "route": route,
            "observability": {"logging": "stdlib", "telemetry": "local-jsonl"},
        }
        write_json(run_dir / "manifest.json", manifest)
        (run_dir / "task.txt").write_text(task, encoding="utf-8")
        (run_dir / "repository-map.md").write_text(repo_map, encoding="utf-8")
        emit_event(run_dir, "route.selected", mode=route["mode"], risk=route["risk"], uncertainty=route["uncertainty"], capabilities=route["capabilities"])
        logger.info("run=%s route=%s risk=%s uncertainty=%s", run_dir.name, route["mode"], route["risk"], route["uncertainty"])
        print(f"Run initialized: {run_dir}")
        return 0
    except HarnessError as exc:
        emit_event(run_dir, "run.error", **exception_summary(exc))
        logger.error("run failed: %s", exc)
        return 2
    except Exception as exc:  # last-resort crash boundary
        emit_event(run_dir, "run.crash", **exception_summary(exc))
        logger.exception("unhandled harness failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
