"""Runtime package bootstrap.

The graph-team integration is enabled by default. Set AER_GRAPH_TEAM=0 to
fall back to the legacy single-provider phase execution for diagnostics.
"""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any


def _install_graph_team_bridge() -> None:
    if os.environ.get("AER_GRAPH_TEAM", "1").strip().lower() in {"0", "false", "off", "no"}:
        return
    try:
        import engine
        from runtime.graph_agent_team import SharedTaskMemory, team_for_route
    except Exception:
        return

    original_invoke = engine.invoke
    eligible = {"execute", "debug", "poc", "research"}

    def graph_invoke(provider: dict[str, Any], prompt_file: Path, phase: str,
                     run_dir: Path, timeout: int, dry_run: bool, logger):
        marker = run_dir / "graph-team.json"
        if phase not in eligible or marker.exists():
            return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

        try:
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            route = manifest.get("route") if isinstance(manifest.get("route"), dict) else engine.heuristic_route(str(manifest.get("task", "")))
            task = str(manifest.get("task", "")).strip()
            intent_digest = str(manifest.get("intent_digest", "")).strip()
            if not intent_digest:
                intent_digest = engine.Orchestrator.intent_digest(task) if hasattr(engine, "Orchestrator") else ""
            base_prompt = prompt_file.read_text(encoding="utf-8")
            team = team_for_route(route)
            memory = SharedTaskMemory(run_dir / "graph-team-memory.jsonl", intent_digest)
            started = engine.time.monotonic()

            def invoke_agent(agent, prompt):
                agent_prompt = run_dir / f"graph-{agent.name}.prompt.md"
                agent_prompt.write_text(prompt, encoding="utf-8")
                return original_invoke(provider, agent_prompt, f"graph-{agent.name}", run_dir, timeout, dry_run, logger)

            result = team.execute(
                task=task,
                intent_digest=intent_digest,
                base_prompt=base_prompt,
                memory=memory,
                invoke_agent=invoke_agent,
            )
            result["phase"] = phase
            result["duration_seconds"] = round(engine.time.monotonic() - started, 3)
            result["provider"] = provider.get("name")
            result["mode"] = "graph-agent-team"
            marker.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            output = "GRAPH_TEAM_JSON: " + json.dumps(result, ensure_ascii=False, sort_keys=True)
            (run_dir / f"{phase}.output.md").write_text(output + "\n", encoding="utf-8")
            return (0 if result.get("accepted") else 1), output, float(result["duration_seconds"])
        except Exception as exc:
            logger.exception("graph agent team failed; falling back to single-agent phase", exc_info=exc)
            fallback = original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)
            marker.write_text(json.dumps({"mode": "graph-agent-team", "status": "fallback", "error": str(exc)}, indent=2) + "\n", encoding="utf-8")
            return fallback

    engine.invoke = graph_invoke


_install_graph_team_bridge()
