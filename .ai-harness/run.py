#!/usr/bin/env python3
"""Provider-neutral AI coding harness.

Python 3.11+; standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"
CONFIG_PATH = HARNESS / "config.toml"
PROMPTS = HARNESS / "prompts"
RUNS = HARNESS / "runs"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def run_capture(command: list[str], *, cwd: Path = ROOT) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return (result.stdout or result.stderr).strip()


def git_state() -> str:
    return "\n".join([
        "$ git status --short\n" + run_capture(["git", "status", "--short"]),
        "$ git branch --show-current\n" + run_capture(["git", "branch", "--show-current"]),
        "$ git rev-parse HEAD\n" + run_capture(["git", "rev-parse", "HEAD"]),
    ])


def build_repo_map(limit: int = 500) -> str:
    """Create a compact repository map with file names and common symbol names."""
    raw = run_capture(["git", "ls-files", "--cached", "--others", "--exclude-standard"])
    files = [line for line in raw.splitlines() if line][:limit]
    lines: list[str] = ["# Repository Map", "", f"Workspace: {ROOT}", ""]

    symbol_pattern = re.compile(
        r"^\s*(?:public |private |protected |internal |static |async |export )*"
        r"(?:class|interface|struct|enum|def|function|func|fn)\s+([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    code_extensions = {
        ".py", ".cs", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    }

    for rel in files:
        path = ROOT / rel
        if not path.is_file():
            continue
        size = path.stat().st_size
        entry = f"- {rel} ({size} bytes)"
        if size <= 250_000 and path.suffix.lower() in code_extensions:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                symbols = symbol_pattern.findall(text)
                if symbols:
                    entry += " :: " + ", ".join(symbols[:20])
            except OSError:
                pass
        lines.append(entry)
    return "\n".join(lines) + "\n"


def make_run_dir() -> Path:
    base_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS / base_id
    suffix = 1
    while path.exists():
        path = RUNS / f"{base_id}-{suffix}"
        suffix += 1
    path.mkdir(parents=True)
    return path


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def infer_capabilities(task: str) -> list[str]:
    text = task.lower()
    result: list[str] = []

    research_terms = (
        "compare", "evaluate", "which library", "which framework", "research", "architecture",
        "design options", "vendor", "api", "protocol", "technology", "migration strategy",
        "unknown", "investigate", "current", "latest",
    )
    poc_terms = (
        "poc", "proof of concept", "feasibility", "feasible", "spike", "prototype",
        "can we", "test whether", "validate whether", "experiment",
    )
    grill_terms = (
        "security", "authentication", "authorization", "migration", "production", "performance",
        "scale", "multi tenant", "database change", "breaking change", "architecture review",
        "challenge this", "high risk",
    )

    if any(term in text for term in research_terms):
        result.append("research")
    if any(term in text for term in poc_terms):
        result.append("poc")
    if any(term in text for term in grill_terms):
        result.append("grill")
    return result


def resolve_phases(
    config: dict,
    workflow: str,
    capabilities: list[str],
    from_phase: str | None,
) -> list[str]:
    workflows = config.get("workflows", {})
    if workflow not in workflows:
        raise ValueError(f"Unknown workflow: {workflow}")

    phases = list(workflows[workflow].get("phases", []))
    if not phases:
        raise ValueError(f"Workflow has no phases: {workflow}")

    for capability in capabilities:
        if capability in phases:
            continue
        insert_at = phases.index("implement") if "implement" in phases else len(phases)
        phases.insert(insert_at, capability)

    if from_phase:
        if from_phase not in phases:
            raise ValueError(f"Phase '{from_phase}' is not part of this workflow")
        phases = phases[phases.index(from_phase):]
    return phases


def render_prompt(
    phase: str,
    task: str,
    history: dict[str, str],
    run_dir: Path,
    capabilities: list[str],
) -> str:
    system = (PROMPTS / "system.md").read_text(encoding="utf-8")
    phase_file = PROMPTS / "phases" / f"{phase}.md"
    if not phase_file.exists():
        raise ValueError(f"No prompt found for phase: {phase}")
    phase_prompt = phase_file.read_text(encoding="utf-8")
    previous = "\n\n".join(
        f"# Previous phase: {name}\n{value}" for name, value in history.items()
    ) or "No previous phase output."
    return f"""{system}

# Task
{task}

# Run directory
{run_dir}

# Repository location
{ROOT}

# Optional capabilities
{', '.join(capabilities) or 'none'}

# Current git state
{git_state()}

# Repository map
A compact repository map is available at `{run_dir / 'repository-map.md'}`.

# Previous phase output
{previous}

{phase_prompt}

# Output contract
Do not claim tests, commands, research sources, or observations that were not performed.
Return concise structured output so downstream phases can consume it.
"""


def run_command(
    command: list[str],
    cwd: Path,
    output_path: Path,
    env: dict[str, str],
) -> tuple[int, str]:
    with output_path.open("w", encoding="utf-8") as output:
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return process.returncode, output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            message = f"Executable not found: {command[0]}\n"
            output.write(message)
            return 127, message


def provider_command(
    provider: dict,
    prompt_file: Path,
    phase: str,
    run_dir: Path,
) -> tuple[list[str], Path]:
    replacements = {
        "{prompt_file}": str(prompt_file),
        "{workspace}": str(ROOT),
        "{phase}": phase,
        "{run_dir}": str(run_dir),
    }
    command = [replacements.get(value, value) for value in provider["command"]]
    cwd_value = provider.get("working_directory", "{workspace}")
    cwd = Path(replacements.get(cwd_value, cwd_value))
    return command, cwd


def validate(config: dict, run_dir: Path, label: str) -> bool:
    commands = config.get("validation", {}).get("commands", [])
    if not commands:
        return True
    log = run_dir / f"validation-{label}.log"
    with log.open("w", encoding="utf-8") as output:
        for command in commands:
            output.write(f"$ {command}\n")
            result = subprocess.run(
                command,
                cwd=ROOT,
                shell=True,
                text=True,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            output.write(f"exit={result.returncode}\n\n")
            if result.returncode != 0:
                return False
    return True


def capabilities_from_args(values: Iterable[str]) -> list[str]:
    allowed = {"research", "poc", "grill"}
    result: list[str] = []
    for value in values:
        if value not in allowed:
            raise ValueError(f"Unknown capability: {value}")
        if value not in result:
            result.append(value)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Provider-neutral AI coding harness")
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("providers", help="List configured AI providers")
    subparsers.add_parser("workflows", help="List workflows and phases")
    subparsers.add_parser("capabilities", help="List optional capabilities")

    context_parser = subparsers.add_parser("context", help="Generate a repository map")
    context_parser.add_argument("--output", default=".ai-harness/repository-map.md")

    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("--agent", required=True, help="Provider name from config.toml")
    run_parser.add_argument("--task", required=True, help="Task or technical question")
    run_parser.add_argument("--workflow", help="Workflow name from config.toml")
    run_parser.add_argument(
        "--capability",
        action="append",
        choices=["research", "poc", "grill"],
        default=[],
        help="Optional capability. Repeat to compose multiple capabilities.",
    )
    run_parser.add_argument("--auto", action="store_true", help="Infer optional capabilities from task wording")
    run_parser.add_argument("--from-phase", help="Resume from a phase in the resolved workflow")
    run_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    config = load_config()

    if args.action == "providers":
        for name in config.get("providers", {}):
            print(name)
        return 0

    if args.action == "workflows":
        for name, workflow in config.get("workflows", {}).items():
            print(f"{name}: {' -> '.join(workflow.get('phases', []))}")
        return 0

    if args.action == "capabilities":
        print("research\npoc\ngrill")
        return 0

    if args.action == "context":
        target = ROOT / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_repo_map(), encoding="utf-8")
        print(target)
        return 0

    providers = config.get("providers", {})
    if args.agent not in providers:
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        print("Configured agents: " + ", ".join(providers), file=sys.stderr)
        return 2

    capabilities = capabilities_from_args(args.capability)
    if args.auto:
        for capability in infer_capabilities(args.task):
            if capability not in capabilities:
                capabilities.append(capability)

    workflow = args.workflow or config.get("workflow", {}).get("default", "coding")
    try:
        phases = resolve_phases(config, workflow, capabilities, args.from_phase)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    executable = providers[args.agent]["command"][0]
    if not args.dry_run and shutil.which(executable) is None:
        print(f"Configured executable is not available: {executable}", file=sys.stderr)
        return 127

    run_dir = make_run_dir()
    (run_dir / "repository-map.md").write_text(build_repo_map(), encoding="utf-8")
    (run_dir / "task.txt").write_text(args.task, encoding="utf-8")

    metadata = {
        "agent": args.agent,
        "workflow": workflow,
        "capabilities": capabilities,
        "phases": phases,
        "started_at": dt.datetime.now(dt.UTC).isoformat(),
        "workspace": str(ROOT),
        "git_initial": git_state(),
        "pid": os.getpid(),
    }
    write_json(run_dir / "manifest.json", metadata)

    history: dict[str, str] = {}
    provider = providers[args.agent]
    harness_config = config.get("workflow", {})
    fix_marker = harness_config.get("review_failure_marker", "HARNESS_FIX_REQUIRED")
    grill_marker = "HARNESS_GRILL_ACTION_REQUIRED"

    env = os.environ.copy()
    env.update({
        "AI_HARNESS_RUN_ID": run_dir.name,
        "AI_HARNESS_RUN_DIR": str(run_dir),
        "AI_HARNESS_AGENT": args.agent,
    })

    for phase in phases:
        if phase == "fix" and fix_marker not in history.get("review", ""):
            print("Skipping fix: review did not request a fix")
            continue

        prompt_file = run_dir / f"{phase}.prompt.md"
        output_file = run_dir / f"{phase}.output.md"
        prompt_file.write_text(
            render_prompt(phase, args.task, history, run_dir, capabilities),
            encoding="utf-8",
        )
        command, cwd = provider_command(provider, prompt_file, phase, run_dir)
        print(f"[{phase}] {' '.join(command)}")

        if args.dry_run:
            output = f"DRY RUN: command was not executed.\nWorkflow={workflow}\nPhase={phase}\n"
            output_file.write_text(output, encoding="utf-8")
            history[phase] = output
            continue

        code, output = run_command(command, cwd, output_file, env)
        history[phase] = output
        if code != 0:
            print(f"Phase failed: {phase}; exit code {code}", file=sys.stderr)
            return code

        if phase == "implement":
            if not validate(config, run_dir, "after-implement"):
                print("Validation failed after implementation", file=sys.stderr)
                return 1
        elif phase == "fix":
            if not validate(config, run_dir, "after-fix"):
                print("Validation failed after fix", file=sys.stderr)
                return 1
        elif phase == "grill" and grill_marker in output:
            (run_dir / "grill-action-required.md").write_text(output, encoding="utf-8")

    final_state = git_state()
    (run_dir / "git-state-final.txt").write_text(final_state, encoding="utf-8")
    metadata["completed_at"] = dt.datetime.now(dt.UTC).isoformat()
    metadata["git_final"] = final_state
    write_json(run_dir / "manifest.json", metadata)
    print(f"Run complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
