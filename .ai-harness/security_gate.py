#!/usr/bin/env python3
"""Pre-execution security gate for AI provider invocations.

The gate is intentionally small and deterministic. It does not claim to be an OS sandbox;
it prevents common configuration mistakes, unsafe read-only overrides, and accidental use of
arbitrary executables from the harness configuration.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

KNOWN_PROVIDERS = {"claude", "codex", "gemini"}
SECRET_ENV_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "CREDENTIAL")
SAFE_BASE_ENV = {
    "PATH", "HOME", "USER", "USERNAME", "USERPROFILE", "SHELL", "TERM",
    "LANG", "LC_ALL", "TMP", "TEMP", "TMPDIR", "SYSTEMROOT", "COMSPEC",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
}
HARNESS_CONTROL_ENV = {
    "HARNESS_RUN_DIR", "HARNESS_PHASE", "HARNESS_TURN_ID",
    "HARNESS_LIVE_MAX_TOOL_CALLS", "HARNESS_LIVE_MAX_TOKENS",
    "HARNESS_LIVE_MIN_PROGRESS_GAIN",
}


class SecurityGateError(RuntimeError):
    """Raised when a provider invocation violates the harness security contract."""


def provider_name(command: list[str]) -> str:
    if not command:
        raise SecurityGateError("Provider command is empty")
    return Path(command[0]).name.lower()


def _option_value(command: list[str], option: str) -> str | None:
    lowered = [arg.lower() for arg in command]
    for index, arg in enumerate(lowered):
        if arg == option and index + 1 < len(command):
            return command[index + 1].lower()
        if arg.startswith(option + "="):
            return arg.split("=", 1)[1].lower()
    return None


def validate_provider_command(command: list[str], *, analysis_only: bool = False) -> None:
    name = provider_name(command)
    if name not in KNOWN_PROVIDERS:
        raise SecurityGateError(
            f"Unsupported provider executable '{name}'. Register a reviewed adapter before use."
        )

    lowered = {arg.lower() for arg in command}
    forbidden = {
        "--dangerously-skip-permissions",
        "--no-sandbox",
        "--approval-mode:auto",
        "--approval-mode=auto",
    }
    if lowered & forbidden:
        raise SecurityGateError("Unsafe provider permission override detected")

    sandbox = _option_value(command, "--sandbox")
    if sandbox == "workspace-write":
        raise SecurityGateError("Unsafe provider permission override detected")
    approval = _option_value(command, "--approval-mode")
    if approval == "auto":
        raise SecurityGateError("Unsafe provider permission override detected")

    if analysis_only:
        if name == "codex" and sandbox != "read-only":
            raise SecurityGateError("Analysis-only Codex invocation must use read-only sandbox")
        if name == "claude" and _option_value(command, "--permission-mode") != "plan":
            raise SecurityGateError("Analysis-only Claude invocation must use plan permission mode")
        if name == "gemini" and approval != "plan":
            raise SecurityGateError("Analysis-only Gemini invocation must use plan approval mode")


def safe_environment(extra_allow: Iterable[str] = ()) -> dict[str, str]:
    """Return a conservative environment for provider execution.

    Provider authentication variables are retained because the provider itself needs them. Other
    credential-like environment variables are removed unless explicitly allowlisted. Approved
    HARNESS_* controls are also retained because they carry bounded execution metadata/limits,
    not credentials. This is not a replacement for a secret broker or OS sandbox.
    """
    allow = SAFE_BASE_ENV | HARNESS_CONTROL_ENV | {str(x) for x in extra_allow}
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in allow:
            result[key] = value
            continue
        upper = key.upper()
        if any(marker in upper for marker in SECRET_ENV_MARKERS):
            continue
    return result


def validate_prompt_file(prompt_file: Path, *, expected_root: Path | None = None) -> Path:
    path = prompt_file.expanduser().resolve()
    if not path.is_file():
        raise SecurityGateError(f"Prompt file does not exist: {path}")
    if expected_root is not None:
        root = expected_root.expanduser().resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SecurityGateError("Prompt file is outside the harness run directory") from exc
    return path
