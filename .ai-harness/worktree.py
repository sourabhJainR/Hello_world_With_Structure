#!/usr/bin/env python3
"""Safe Git worktree lifecycle helper for AI coding runs.

The helper creates isolated worktrees for risky or parallel agent work and
records enough metadata to resume or remove them safely.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKTREES = ROOT / ".ai-harness" / "worktrees"
STATE = ROOT / ".ai-harness" / "worktrees.json"


def run(command: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    except OSError as exc:
        return 127, f"ERROR: {exc}"
    return result.returncode, (result.stdout or result.stderr).strip()


def load() -> dict[str, dict]:
    if not STATE.exists():
        return {}
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def save(value: dict[str, dict]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def safe_name(value: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return result[:70] or "agent"


def create(name: str, base: str = "HEAD", detached: bool = False) -> dict:
    WORKTREES.mkdir(parents=True, exist_ok=True)
    key = safe_name(name)
    path = WORKTREES / f"{key}-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}"
    if detached:
        command = ["git", "worktree", "add", "--detach", str(path), base]
        branch = None
    else:
        branch = f"ai-harness/{key}-{dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')}"
        command = ["git", "worktree", "add", "-b", branch, str(path), base]
    code, output = run(command)
    if code != 0:
        raise RuntimeError(output)
    state = load()
    record = {
        "name": key,
        "path": str(path),
        "base": base,
        "branch": branch,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    state[key] = record
    save(state)
    return record


def remove(name: str, force: bool = False) -> dict:
    state = load()
    record = state.get(name)
    if not record:
        raise KeyError(f"Unknown worktree: {name}")
    command = ["git", "worktree", "remove"]
    if force:
        command.append("--force")
    command.append(record["path"])
    code, output = run(command)
    if code != 0:
        raise RuntimeError(output)
    state.pop(name, None)
    save(state)
    return record


def list_worktrees() -> list[dict]:
    code, output = run(["git", "worktree", "list", "--porcelain"])
    if code != 0:
        raise RuntimeError(output)
    records = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="AI harness Git worktree helper")
    sub = parser.add_subparsers(dest="action", required=True)

    create_parser = sub.add_parser("create")
    create_parser.add_argument("name")
    create_parser.add_argument("--base", default="HEAD")
    create_parser.add_argument("--detached", action="store_true")

    remove_parser = sub.add_parser("remove")
    remove_parser.add_argument("name")
    remove_parser.add_argument("--force", action="store_true")

    sub.add_parser("list")

    args = parser.parse_args()
    try:
        if args.action == "create":
            print(json.dumps(create(args.name, args.base, args.detached), indent=2))
        elif args.action == "remove":
            print(json.dumps(remove(args.name, args.force), indent=2))
        else:
            print(json.dumps(list_worktrees(), indent=2))
        return 0
    except (RuntimeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
