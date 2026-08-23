#!/usr/bin/env python3
"""Production launcher: one run owns one session and one IO-aware context policy."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import context_engine
import engine

_original_make_run_dir = engine.make_run_dir
_original_build_prompt = engine.build_prompt
_session_dir: Path | None = None


def session_make_run_dir() -> Path:
    global _session_dir
    if _session_dir is None:
        _session_dir = _original_make_run_dir()
    return _session_dir


def optimized_repository_map(limit: int = 500) -> str:
    return context_engine.build_repository_context(
        engine.ROOT,
        "",
        limit_files=min(limit, 180),
        budget_chars=9000,
    )


def optimized_build_prompt(phase, task, source, jira, route, repo_map, memory, profile, history):
    repo_tile, memory_tile, history_tile, metadata = context_engine.flash_context_prompt(
        task,
        repo_map,
        memory,
        history,
        budget_chars=12000,
    )
    prompt = _original_build_prompt(
        phase,
        task,
        source,
        jira,
        route,
        repo_tile,
        memory_tile,
        profile,
        history_tile,
    )
    return prompt + f"\n## IO-aware context\n{metadata}\n"


# The previous coordinator allocated a session in both main() and run_task().
# The launcher makes allocation idempotent so one invocation owns exactly one directory.
engine.make_run_dir = session_make_run_dir
engine.repository_map = optimized_repository_map
engine.build_prompt = optimized_build_prompt


if __name__ == "__main__":
    raise SystemExit(engine.main())
