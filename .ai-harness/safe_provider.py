#!/usr/bin/env python3
"""Security-gated entry point used by configured provider adapters."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from security_gate import SecurityGateError, safe_environment, validate_prompt_file, validate_provider_command
from provider import analysis_only_command, is_analysis_only
from runtime.prompting_policy import compose

_TRANSIENT_MARKERS = (
    "response stopped arriving", "response stopped", "api error", "connection reset",
    "connection closed", "connection error", "timed out", "timeout",
    "temporarily unavailable", "service unavailable", "internal server error",
    "overloaded", "rate limit", "stream disconnected", "stream interrupted",
)


def _transient_failure(output: str, return_code: int) -> bool:
    if return_code == 0:
        return False
    text = output.lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def _continuation_prompt(original: str, previous: str, attempt: int) -> str:
    tail = previous[-24000:]
    return (
        original
        + "\n\n# AER RESPONSE RECOVERY\n"
        + f"Attempt {attempt} continues a response interrupted before completion.\n"
        + "Do not restart completed work. Continue from the last confirmed state and "
          "finish the requested response. Preserve correct prior conclusions.\n"
        + "Previous partial provider output:\n---\n"
        + tail
        + "\n---\n"
        + "Return the complete remaining response.\n"
    )


def _run_resilient(command: list[str], prompt: str, run_dir: Path) -> int:
    max_retries = max(0, min(8, int(os.environ.get("HARNESS_PROVIDER_MAX_RETRIES", "4"))))
    delay = max(0.0, min(30.0, float(os.environ.get("HARNESS_PROVIDER_RETRY_DELAY", "1.0"))))
    transcript = ""

    for attempt in range(max_retries + 1):
        effective = prompt if attempt == 0 else _continuation_prompt(prompt, transcript, attempt)
        fd, effective_name = tempfile.mkstemp(prefix="effective-prompt-", suffix=".md", dir=run_dir)
        os.close(fd)
        effective_path = Path(effective_name)
        try:
            effective_path.write_text(compose(effective), encoding="utf-8")
            env = safe_environment()
            env.update({
                "HARNESS_PROVIDER_ATTEMPT": str(attempt + 1),
                "HARNESS_SECURITY_GATE": "enforced",
                "HARNESS_PROMPT_ROOT": str(run_dir),
                "HARNESS_CANONICAL_PROMPT": str(Path(os.environ.get("HARNESS_CANONICAL_PROMPT", effective_path)).resolve()),
                # Normal model/tool progress must not be interrupted by the
                # diminishing-returns heuristic. Hard safety/token limits remain
                # active when explicitly configured.
                "HARNESS_LIVE_MIN_PROGRESS_GAIN": "-1",
            })
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve().with_name("provider.py")), "--prompt-file", str(effective_path), "--", *command],
                cwd=Path(os.environ.get("HARNESS_WORKSPACE", Path(__file__).resolve().parent.parent)),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_parts: list[str] = []
            assert process.stdout is not None
            for line in process.stdout:
                output_parts.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()
            code = process.wait()
            output = "".join(output_parts)
            transcript += output
            if code == 0:
                return 0
            if not _transient_failure(output, code) or attempt >= max_retries:
                return code
            print(f"AER provider response interrupted; continuing attempt {attempt + 2}/{max_retries + 1}", file=sys.stderr)
            if delay:
                time.sleep(min(30.0, delay * (2 ** attempt)))
        finally:
            try:
                effective_path.unlink(missing_ok=True)
            except OSError:
                pass
    return 1


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

        fd, effective_path = tempfile.mkstemp(prefix="effective-prompt-", suffix=".md", dir=prompt_file.parent)
        os.close(fd)
        effective_prompt = Path(effective_path)
        effective_prompt.write_text(compose(prompt), encoding="utf-8")

        env_run_dir = Path(os.environ.get("HARNESS_RUN_DIR", str(prompt_file.parent))).resolve()
        env_run_dir.mkdir(parents=True, exist_ok=True)
        return _run_resilient(command, prompt, env_run_dir)
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
