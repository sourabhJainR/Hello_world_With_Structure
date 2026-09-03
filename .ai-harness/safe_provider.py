#!/usr/bin/env python3
"""Security-gated entry point used by configured provider adapters."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from security_gate import SecurityGateError, safe_environment, validate_prompt_file, validate_provider_command
from provider import analysis_only_command, is_analysis_only
from runtime.prompting_policy import compose


def main() -> int:
    parser = argparse.ArgumentParser(description="Security-gated AI provider launcher")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("No provider command supplied", file=sys.stderr)
        return 2

    effective_prompt = None
    try:
        prompt_file = validate_prompt_file(
            Path(args.prompt_file),
            expected_root=Path(os.environ.get("HARNESS_RUN_DIR", Path(args.prompt_file).parent)).resolve(),
        )
        prompt = prompt_file.read_text(encoding="utf-8")
        analysis_only = is_analysis_only(prompt)
        validate_provider_command(command, analysis_only=analysis_only)
        if analysis_only:
            command = analysis_only_command(command)

        # Keep the canonical prompt immutable. The provider receives a derived
        # prompt carrying the common prompting contract, so audit evidence can
        # still distinguish the authored task from the effective model input.
        fd, effective_path = tempfile.mkstemp(prefix="effective-prompt-", suffix=".md", dir=prompt_file.parent)
        os.close(fd)
        effective_prompt = Path(effective_path)
        effective_prompt.write_text(compose(prompt), encoding="utf-8")

        bridge = Path(__file__).resolve().with_name("provider.py")
        env = safe_environment()
        env.update({
            "HARNESS_SECURITY_GATE": "enforced",
            "HARNESS_PROMPT_ROOT": str(prompt_file.parent.resolve()),
            "HARNESS_CANONICAL_PROMPT": str(prompt_file.resolve()),
        })
        return subprocess.run(
            [sys.executable, str(bridge), "--prompt-file", str(effective_prompt), "--", *command],
            cwd=Path(os.environ.get("HARNESS_WORKSPACE", Path(__file__).resolve().parent.parent)),
            env=env,
            check=False,
        ).returncode
    except SecurityGateError as exc:
        print(f"SECURITY GATE: {exc}", file=sys.stderr)
        return 78
    except (OSError, UnicodeError) as exc:
        print(f"SECURITY GATE ERROR: {exc}", file=sys.stderr)
        return 78
    finally:
        if effective_prompt is not None:
            try:
                effective_prompt.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
