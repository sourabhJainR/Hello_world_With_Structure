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


class SecurityGateError(RuntimeError):
    """Raised when a provider invocation violates the harness security contract."""


def provider_name(command: list[str]) -> str:
    if not command:
        raise SecurityGateError("Provider command is empty")
    return Path(command[0]).name.lower()


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
        "--sandbox=workspace-write",
        "--sandbox workspace-write",
    }
    if lowered & forbidden:
        raise SecurityGateError("Unsafe provider permission override detected")

    if analysis_only:
        if name == "codex" and any(arg == "--sandbox" and i + 1 < len(command) and command[i + 1] != "read-only" for i, arg in enumerate(command)):
            raise SecurityGateError("Analysis-only Codex invocation must use read-only sandbox")
        if name == "claude" and "--permission-mode" in lowered:
            idx = [x.lower() for x in command].index("--permission-mode")
            if idx + 1 >= len(command) or command[idx + 1].lower() != "plan":
                raise SecurityGateError("Analysis-only Claude invocation must use plan permission mode")
        if name == "gemini" and "--approval-mode" in lowered:
            idx = [x.lower() for x in command].index("--approval-mode")
            if idx + 1 >= len(command) or command[idx + 1].lower() != "plan":
                raise SecurityGateError("Analysis-only Gemini invocation must use plan approval mode")


def safe_environment(extra_allow: Iterable[str] = ()) -> dict[str, str]:
    """Return a conservative environment for provider execution.

    Provider authentication variables are retained because the provider itself needs them. Other
    credential-like environment variables are removed unless explicitly allowlisted. This is not
    a replacement for a secret broker or OS sandbox.
    """
    allow = SAFE_BASE_ENV | {str(x) for x in extra_allow}
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in allow:
            result[key] = value
            continue
        upper = key.upper()
        if any(marker in upper for marker in SECRET_ENV_MARKERS):
            continue
        # Do not pass arbitrary environment state to an agent unless explicitly allowlisted.
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
