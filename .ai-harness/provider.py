#!/usr/bin/env python3
"""Generic provider bridge with a hard read-only boundary for RCA/analysis requests."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def is_analysis_only(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in (
        "rca analysis-only",
        "root cause analysis only",
        "do not implement a fix",
        "do not modify source",
        "patch_allowed: false",
    ))


def analysis_only_command(command: list[str]) -> list[str]:
    if not command:
        return command
    name = Path(command[0]).name.lower()
    result = list(command)
    if name == "claude":
        result[1:1] = ["--permission-mode", "plan"]
    elif name == "codex" and len(result) >= 2 and result[1] == "exec":
        result[2:2] = ["--sandbox", "read-only"]
    elif name == "gemini":
        result[1:1] = ["--approval-mode", "plan"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic AI CLI provider bridge")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("No provider command supplied", file=sys.stderr)
        return 2
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if is_analysis_only(prompt):
        command = analysis_only_command(command)
        prompt = (
            "RCA ANALYSIS-ONLY ENFORCEMENT\n"
            "Do not edit files, create patches, commit, merge, or perform destructive actions. "
            "Investigate deeply and return evidence-backed findings only. "
            "Separate facts, inferences, contradictions, unknowns, hypotheses, root cause, and follow-up.\n\n"
            + prompt
        )
    try:
        result = subprocess.run(command + [prompt], text=True, check=False)
    except OSError as exc:
        print(f"Unable to start provider: {exc}", file=sys.stderr)
        return 127
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
