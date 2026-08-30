#!/usr/bin/env python3
"""Production launcher: one run owns one session and one IO-aware context policy."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import context_engine
import engine
import knowledge_fabric
import p1_lifecycle

_original_make_run_dir = engine.make_run_dir
_original_build_prompt = engine.build_prompt
_original_run_task = engine.run_task
_session_dir: Path | None = None
_knowledge: dict = {}


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


def _task_from_args(args) -> str:
    task = str(getattr(args, "task", "") or "").strip()
    jira_file = getattr(args, "jira_file", None)
    if jira_file:
        path = Path(jira_file)
        if path.is_file():
            task = (task + "\n\nJira context:\n" + path.read_text(encoding="utf-8")).strip()
    jira = getattr(args, "jira", None)
    if not task and jira:
        task = f"Work on Jira item {jira}"
    return task


def _prepare_knowledge(args, config: dict) -> None:
    global _knowledge
    if getattr(args, "resume", None):
        path = Path(args.resume).resolve() / "knowledge.json"
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    _knowledge = value
                    return
            except json.JSONDecodeError:
                pass
    task = _task_from_args(args)
    if not task:
        _knowledge = {"sources": [], "evidence": "No task-specific knowledge requested."}
        return
    _knowledge = knowledge_fabric.collect(task, config)
    if _session_dir is not None:
        ( _session_dir / "knowledge.json").write_text(
            json.dumps(_knowledge, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        ( _session_dir / "knowledge.md").write_text(
            "# Knowledge Fabric\n\n"
            + "Sources: " + ", ".join(_knowledge.get("sources", [])) + "\n\n"
            + str(_knowledge.get("evidence", "")) + "\n",
            encoding="utf-8",
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
    knowledge = str(_knowledge.get("evidence", "No external structural knowledge available."))
    knowledge = knowledge[:6000]
    sources = ", ".join(_knowledge.get("sources", [])) or "none"
    return prompt + f"\n## Knowledge fabric\nSources: {sources}\n{knowledge}\n\n## IO-aware context\n{metadata}\n"


def optimized_run_task(args, config, logger):
    _prepare_knowledge(args, config)
    task = _task_from_args(args)
    if not task:
        return _original_run_task(args, config, logger)
    profile = engine.profile_repository()
    route = engine.heuristic_route(task)
    run_dir = session_make_run_dir()
    p1_lifecycle.start(run_dir, task, "resume" if getattr(args, "resume", None) else "prompt", profile, route)
    code = _original_run_task(args, config, logger)
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        try:
            p1_lifecycle.finish(run_dir, json.loads(manifest_path.read_text(encoding="utf-8")))
        except Exception as exc:
            (run_dir / "p1-lifecycle.error.txt").write_text(str(exc) + "\n", encoding="utf-8")
            return 1 if code == 0 else code
    return code


# One invocation owns exactly one directory. Resume reuses its existing directory.
engine.make_run_dir = session_make_run_dir
engine.repository_map = optimized_repository_map
engine.build_prompt = optimized_build_prompt
engine.run_task = optimized_run_task


if __name__ == "__main__":
    raise SystemExit(engine.main())
