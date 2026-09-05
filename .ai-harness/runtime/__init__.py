"""Runtime package bootstrap.

The graph-team integration is enabled by default. Set AER_GRAPH_TEAM=0 to
fall back to the legacy single-provider phase execution for diagnostics.

The graph team is the default collaboration layer for every provider-driven
execution phase after routing. Deterministic lifecycle controls such as
validation and learning remain owned by the harness itself.
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

    def graph_invoke(provider: dict[str, Any], prompt_file: Path, phase: str,
                     run_dir: Path, timeout: int, dry_run: bool, logger):
        # Routing is intentionally deterministic/provider-assisted but must not
        # recursively invoke a graph before the task route and manifest exist.
        if phase == "route":
            return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

        # Each provider-driven phase gets its own graph execution and memory
        # entry. Do not use a single run-level marker: that would silently turn
        # later phases back into single-agent execution.
        marker = run_dir / f"graph-team-{phase}.json"
        if marker.exists():
            return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

        try:
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            route = manifest.get("route") if isinstance(manifest.get("route"), dict) else engine.heuristic_route(str(manifest.get("task", "")))
            route = dict(route)
            route["phase"] = phase

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
                agent_prompt = run_dir / f"graph-{phase}-{agent.name}.prompt.md"
                agent_prompt.write_text(prompt, encoding="utf-8")
                return original_invoke(provider, agent_prompt, f"graph-{phase}-{agent.name}", run_dir, timeout, dry_run, logger)

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
            result["collaboration"] = {
                "enabled": True,
                "phase_scoped": True,
                "shared_memory": True,
                "dependency_graph": True,
                "parallel_read_only": True,
                "serialized_mutations": True,
            }
            marker.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            output = "GRAPH_TEAM_JSON: " + json.dumps(result, ensure_ascii=False, sort_keys=True)
            (run_dir / f"{phase}.output.md").write_text(output + "\n", encoding="utf-8")
            return (0 if result.get("accepted") else 1), output, float(result["duration_seconds"])
        except Exception as exc:
            logger.exception("graph agent team failed; falling back to single-agent phase", exc_info=exc)
            fallback = original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)
            marker.write_text(json.dumps({"mode": "graph-agent-team", "status": "fallback", "phase": phase, "error": str(exc)}, indent=2) + "\n", encoding="utf-8")
            return fallback

    engine.invoke = graph_invoke
