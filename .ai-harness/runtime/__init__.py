"""Runtime package bootstrap.

The graph-team integration is enabled by default. Set AER_GRAPH_TEAM=0 to
fall back to the legacy single-provider phase execution for diagnostics.

Every provider-driven lifecycle phase gets a phase-appropriate dependency
DAG. Deterministic harness-owned operations such as validation and learning
remain authoritative, while their surrounding execution still participates
in the shared run contract.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _phase_team(route: dict[str, Any], phase: str, graph_types):
    AgentSpec, GraphAgentTeam = graph_types
    risk = str(route.get("risk", "low"))
    common = [
        AgentSpec("planner", "planner", read_only=True, focus="Turn the current phase contract into a minimal dependency-aware plan."),
        AgentSpec("explorer", "explorer", depends_on=("planner",), read_only=True, focus="Trace repository structure, callers, tests, constraints and protected behavior for this phase."),
    ]

    phase = str(phase)
    if phase == "context":
        agents = common + [
            AgentSpec("context-auditor", "context auditor", depends_on=("explorer",), read_only=True, focus="Validate repository context, scope, relevant evidence and missing information."),
        ]
    elif phase == "research":
        agents = common + [
            AgentSpec("researcher", "researcher", depends_on=("planner",), read_only=True, focus="Gather task-relevant technical evidence, alternatives and current practices."),
            AgentSpec("research-reviewer", "research reviewer", depends_on=("explorer", "researcher"), read_only=True, focus="Challenge evidence quality, applicability and unsupported assumptions."),
        ]
    elif phase == "poc":
        agents = common + [
            AgentSpec("researcher", "researcher", depends_on=("planner",), read_only=True, focus="Establish feasibility, constraints and implementation alternatives."),
            AgentSpec("builder", "poc builder", depends_on=("explorer", "researcher"), read_only=False, focus="Build the smallest reversible proof of concept."),
            AgentSpec("verifier", "poc verifier", depends_on=("builder",), read_only=True, focus="Exercise the proof of concept and identify failure modes."),
        ]
    elif phase == "debug":
        agents = common + [
            AgentSpec("rca", "RCA investigator", depends_on=("planner", "explorer"), read_only=True, focus="Prove root cause with evidence before proposing a fix."),
            AgentSpec("builder", "fix builder", depends_on=("explorer", "rca"), read_only=False, focus="Implement the smallest evidence-backed correction."),
            AgentSpec("verifier", "verifier", depends_on=("builder",), read_only=True, focus="Verify the fix and search for regressions and adjacent failure modes."),
        ]
    elif phase == "execute":
        agents = common + [
            AgentSpec("builder", "builder", depends_on=("explorer",), read_only=False, focus="Implement the smallest safe task-scoped change."),
            AgentSpec("verifier", "verifier", depends_on=("builder",), read_only=True, focus="Verify behavior, tests, compatibility and regression risk."),
        ]
    elif phase == "repair":
        agents = common + [
            AgentSpec("rca", "repair RCA investigator", depends_on=("planner", "explorer"), read_only=True, focus="Diagnose the failed validation or review using fresh evidence."),
            AgentSpec("builder", "repair builder", depends_on=("explorer", "rca"), read_only=False, focus="Apply the smallest targeted repair; do not broaden scope."),
            AgentSpec("verifier", "repair verifier", depends_on=("builder",), read_only=True, focus="Re-run or inspect the failing behavior and confirm the repair."),
        ]
    elif phase == "grill":
        agents = common + [
            AgentSpec("risk-reviewer", "risk reviewer", depends_on=("explorer",), read_only=True, focus="Stress-test assumptions, failure modes, operational risks and edge cases."),
        ]
    elif phase == "review":
        agents = common + [
            AgentSpec("correctness-reviewer", "correctness reviewer", depends_on=("explorer",), read_only=True, focus="Check correctness, compatibility, edge cases and test coverage."),
        ]
    else:
        agents = common + [
            AgentSpec("phase-reviewer", "phase reviewer", depends_on=("explorer",), read_only=True, focus="Review the current phase result for correctness, safety and completeness."),
        ]

    review_names = {a.name for a in agents if "reviewer" in a.name or a.name == "risk-reviewer" or a.name == "context-auditor"}
    if risk in {"high", "critical"} and phase in {"execute", "debug", "poc", "repair", "review", "grill"}:
        dependency = tuple(name for name in ("builder", "verifier") if name in {a.name for a in agents}) or ("explorer",)
        agents.extend([
            AgentSpec("security-reviewer", "security reviewer", depends_on=dependency, read_only=True, focus="Check trust boundaries, permissions, injection, secrets and unsafe defaults."),
            AgentSpec("architecture-reviewer", "architecture reviewer", depends_on=dependency, read_only=True, focus="Check coupling, dependency direction, maintainability and unnecessary complexity."),
        ])
        review_names.update({"security-reviewer", "architecture-reviewer"})

    final_deps = tuple(a.name for a in agents if a.name in review_names)
    if not final_deps:
        final_deps = (agents[-1].name,)
    agents.append(AgentSpec("synthesizer", "team synthesizer", depends_on=final_deps, read_only=True, focus="Synthesize evidence, decisions, unresolved risks and the recommended next action for this phase."))
    return GraphAgentTeam(agents)


def _install_graph_team_bridge() -> None:
    if os.environ.get("AER_GRAPH_TEAM", "1").strip().lower() in {"0", "false", "off", "no"}:
        return
    try:
        import engine
        from runtime.graph_agent_team import AgentSpec, GraphAgentTeam, SharedTaskMemory
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
        # Routing is deliberately kept outside the collaboration DAG so route
        # selection remains cheap and cannot recursively route itself.
        if phase == "route":
            return original_invoke(provider, prompt_file, phase, run_dir, timeout, dry_run, logger)

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
                intent_digest = hashlib.sha256(task.encode("utf-8")).hexdigest()

            base_prompt = prompt_file.read_text(encoding="utf-8")
            team = _phase_team(route, phase, (AgentSpec, GraphAgentTeam))
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
