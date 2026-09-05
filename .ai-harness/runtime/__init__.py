"""Runtime package bootstrap.

The graph-team integration is enabled by default. Set AER_GRAPH_TEAM=0 to
fall back to the legacy single-provider phase execution for diagnostics.

Important: installation is explicit. This module is imported while engine.py
is still initializing, so importing runtime must never mutate engine.invoke.
The public .ai-harness/run.py wrapper installs the bridge only after engine
has completed importing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _install_graph_team_bridge() -> None:
    if os.environ.get("AER_GRAPH_TEAM", "1").strip().lower() in {"0", "false", "off", "no"}:
        return
    try:
        import engine
        from runtime.graph_agent_team import GraphAgentTeam, SharedTaskMemory, team_for_route
    except Exception:
        return

    # Mark read-only graph prompts as analysis-only so safe_provider enforces
    # the provider's native plan/read-only mode instead of relying on prose.
    if not getattr(GraphAgentTeam.execute, "_aer_guarded", False):
        original_execute = GraphAgentTeam.execute

        def guarded_execute(self, *, task, intent_digest, base_prompt, memory, invoke_agent):
            def guarded_invoke(agent, prompt):
                if agent.read_only:
                    prompt += "\n\n## Security execution mode\npatch_allowed: false\n"
                return invoke_agent(agent, prompt)

            return original_execute(
                self,
                task=task,
                intent_digest=intent_digest,
                base_prompt=base_prompt,
                memory=memory,
                invoke_agent=guarded_invoke,
            )

        guarded_execute._aer_guarded = True
        GraphAgentTeam.execute = guarded_execute

    original_invoke = engine.invoke
    trigger_for_mode = {
        "implement": "execute",
        "debug": "debug",
        "research": "research",
        "poc": "poc",
        "review": "review",
        "grill": "grill",
    }

    def graph_invoke(provider: dict[str, Any], prompt_file: Path, phase: str,
                     run_dir: Path, timeout: int, dry_run: bool, logger):
        marker = run_dir / "graph-team.json"
        if marker.exists():
            return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

        try:
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            route = manifest.get("route") if isinstance(manifest.get("route"), dict) else engine.heuristic_route(str(manifest.get("task", "")))
            mode = str(route.get("mode", "implement"))
            trigger_phase = trigger_for_mode.get(mode, "execute")
            if phase != trigger_phase:
                return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

            task = str(manifest.get("task", "")).strip()
            intent_digest = str(manifest.get("intent_digest", "")).strip()
            if not intent_digest:
                contract_path = run_dir / "intent-contract.json"
                if contract_path.exists():
                    contract = json.loads(contract_path.read_text(encoding="utf-8"))
                    intent_digest = str(contract.get("intent_digest", "")).strip()
            if not intent_digest:
                import hashlib
                intent_digest = hashlib.sha256(task.encode("utf-8")).hexdigest()

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
