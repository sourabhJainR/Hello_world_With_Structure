#!/usr/bin/env python3
"""Provider-neutral AI coding harness.

Requires Python 3.11+ for tomllib. No third-party packages are required.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"
CONFIG_PATH = HARNESS / "config.toml"
PROMPTS = HARNESS / "prompts"
RUNS = HARNESS / "runs"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def git_state() -> str:
    commands = [
        ["git", "status", "--short"],
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        ["git", "rev-parse", "HEAD"],
    ]
    output = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        output.append("$ " + " ".join(command))
        output.append((result.stdout or result.stderr).strip())
    return "\n".join(output)


def make_run_dir() -> Path:
    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS / run_id
    path.mkdir(parents=True, exist_ok=False)
    return path


def render_prompt(phase: str, task: str, history: dict[str, str]) -> str:
    system = (PROMPTS / "system.md").read_text(encoding="utf-8")
    phase_prompt = (PROMPTS / "phases" / f"{phase}.md").read_text(encoding="utf-8")
    previous = "\n\n".join(
        f"# Previous phase: {name}\n{value}" for name, value in history.items()
    ) or "No previous phase output."
    return f"""{system}

# Task
{task}

# Repository location
{ROOT}

# Current git state
{git_state()}

# Previous phase output
{previous}

{phase_prompt}
"""


def run_command(command: list[str], cwd: Path, output_path: Path) -> tuple[int, str]:
    with output_path.open("w", encoding="utf-8") as output:
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return process.returncode, output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            message = f"Executable not found: {command[0]}\n"
            output.write(message)
            return 127, message


def provider_command(provider: dict, prompt_file: Path, phase: str) -> tuple[list[str], Path]:
    replacements = {
        "{prompt_file}": str(prompt_file),
        "{workspace}": str(ROOT),
        "{phase}": phase,
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
            result = subprocess.run(command, cwd=ROOT, shell=True, text=True,
                                    stdout=output, stderr=subprocess.STDOUT)
            output.write(f"exit={result.returncode}\n\n")
            if result.returncode != 0:
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Provider-neutral AI coding harness")
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("providers", help="List configured AI providers")
    run_parser = subparsers.add_parser("run", help="Run the coding workflow")
    run_parser.add_argument("--agent", required=True, help="Provider name from config.toml")
    run_parser.add_argument("--task", required=True, help="Coding task")
    run_parser.add_argument("--from-phase", choices=["understand", "plan", "implement", "review", "fix"])
    run_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    config = load_config()

    if args.action == "providers":
        for name in config.get("providers", {}):
            print(name)
        return 0

    providers = config.get("providers", {})
    if args.agent not in providers:
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        print("Configured agents: " + ", ".join(providers), file=sys.stderr)
        return 2

    executable = providers[args.agent]["command"][0]
    if not args.dry_run and shutil.which(executable) is None:
        print(f"Configured executable is not available: {executable}", file=sys.stderr)
        return 127

    run_dir = make_run_dir()
    (run_dir / "task.txt").write_text(args.task, encoding="utf-8")
    (run_dir / "metadata.json").write_text(json.dumps({
        "agent": args.agent,
        "started_at": dt.datetime.now(dt.UTC).isoformat(),
        "workspace": str(ROOT),
    }, indent=2), encoding="utf-8")

    phases = config["workflow"]["phases"]
    if args.from_phase:
        phases = phases[phases.index(args.from_phase):]

    history: dict[str, str] = {}
    provider = providers[args.agent]
    fix_marker = config["workflow"].get("review_failure_marker", "HARNESS_FIX_REQUIRED")

    for phase in phases:
        if phase == "fix":
            review = history.get("review", "")
            if fix_marker not in review:
                print("Skipping fix: review did not request a fix")
                continue

        prompt_file = run_dir / f"{phase}.prompt.md"
        output_file = run_dir / f"{phase}.output.md"
        prompt_file.write_text(render_prompt(phase, args.task, history), encoding="utf-8")
        command, cwd = provider_command(provider, prompt_file, phase)
        print(f"[{phase}] {' '.join(command)}")

        if args.dry_run:
            output = "DRY RUN: command was not executed."
            output_file.write_text(output, encoding="utf-8")
            history[phase] = output
            continue

        code, output = run_command(command, cwd, output_file)
        history[phase] = output
        if code != 0:
            print(f"Phase failed: {phase}; exit code {code}", file=sys.stderr)
            return code

        if phase == "implement":
            if not validate(config, run_dir, "after-implement"):
                print("Validation failed after implementation", file=sys.stderr)
                return 1
        if phase == "fix":
            if not validate(config, run_dir, "after-fix"):
                print("Validation failed after fix", file=sys.stderr)
                return 1

    (run_dir / "git-state-final.txt").write_text(git_state(), encoding="utf-8")
    print(f"Run complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
