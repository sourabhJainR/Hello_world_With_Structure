#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook for AER.

This is intentionally lightweight: it does not edit repositories or run the
AER engine. It tells Claude that the AER control-plane skill is available and
provides the active AER version so the skill can be selected for engineering
work.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        payload = {}

    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return 0

    home = Path(os.environ.get("AER_HOME", Path.home() / ".aer")).expanduser()
    version = "unknown"
    active = home / "active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        version = str(data.get("version") or version)
    except (OSError, json.JSONDecodeError):
        pass

    context = (
        f"AER control plane is installed and active (version {version}). "
        "For repository engineering work, use the AER skill "
        "`/adaptive-ai-coding-orchestrator:ai-coding-orchestrator` when appropriate. "
        "Follow repository instructions first; preserve the user's intent and scope; "
        "collect repository evidence before editing; make the smallest safe change; "
        "verify the result; and report evidence, verification, risks, and incomplete checks. "
        "For investigation/RCA without an explicit fix request, diagnose without editing. "
        "Do not claim commands or tests were run unless observed."
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
