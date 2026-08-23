#!/usr/bin/env python3
"""Run independent, read-only AI reviews against the current repository or worktree."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / ".ai-harness" / "runs"

PROMPTS = {
    "correctness": "Review only for functional correctness, edge cases, regressions, contracts, and test adequacy. Do not modify files.",
    "security": "Review only for security, trust boundaries, secrets, authorization, input validation, injection, unsafe defaults, and data exposure. Do not modify files.",
    "performance": "Review only for performance, concurrency, resource usage, latency, scale, caching, retries, and failure amplification. Do not modify files.",
    "architecture": "Review only for design quality, coupling, cohesion, dependency direction, compatibility, maintainability, and unnecessary complexity. Do not modify files.",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent read-only AI reviewers")
    parser.add_argument("--agent", required=True, help="Provider command name, for example claude")
    parser.add_argument("--workspace", default=str(ROOT))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--review", action="append", choices=sorted(PROMPTS), default=[])
    parser.add_argument("--task", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    provider_map = {
        "claude": ["claude", "-p"],
        "codex": ["codex", "exec"],
        "gemini": ["gemini", "-p"],
    }
    command_prefix = provider_map.get(args.agent)
    if not command_prefix:
        print(f"Unsupported built-in reviewer provider: {args.agent}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    reviews = args.review or ["correctness"]
    results = []

    for review in reviews:
        prompt = f"""You are an independent read-only reviewer operating on an existing repository.

Task:
{args.task}

Review focus:
{PROMPTS[review]}

Inspect the actual repository and current diff. Do not trust earlier agent claims.
Return:
- findings with severity (critical/high/medium/low)
- concrete file/line references where possible
- evidence
- recommended fix
- whether the change is safe to approve

Never modify files. Never claim tests or commands were run unless you ran them.
"""
        prompt_file = run_dir / f"review-{review}.prompt.md"
        output_file = run_dir / f"review-{review}.output.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        command = command_prefix + [prompt]
        started = time.monotonic()
        if args.dry_run:
            output = "DRY RUN\n$ " + " ".join(command[:2]) + " <prompt>"
            code = 0
        else:
            try:
                result = subprocess.run(command, cwd=args.workspace, text=True, capture_output=True, check=False, timeout=args.timeout, env=os.environ.copy())
                code = result.returncode
                output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
            except subprocess.TimeoutExpired:
                code = 124
                output = f"TIMEOUT after {args.timeout}s"
            except OSError as exc:
                code = 127
                output = f"ERROR: {exc}"
        output_file.write_text(output, encoding="utf-8")
        results.append({"review": review, "exit_code": code, "duration_seconds": round(time.monotonic() - started, 3), "output": str(output_file)})

    (run_dir / "independent-reviews.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0 if all(item["exit_code"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
