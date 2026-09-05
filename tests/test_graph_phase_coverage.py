from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_INIT = ROOT / ".ai-harness" / "runtime" / "__init__.py"
GRAPH_TEAM = ROOT / ".ai-harness" / "runtime" / "graph_agent_team.py"


def _load_modules():
    graph_spec = importlib.util.spec_from_file_location("aer_graph_agent_team", GRAPH_TEAM)
    assert graph_spec and graph_spec.loader
    graph = importlib.util.module_from_spec(graph_spec)
    graph_spec.loader.exec_module(graph)

    runtime_spec = importlib.util.spec_from_file_location("aer_runtime_init", RUNTIME_INIT)
    assert runtime_spec and runtime_spec.loader
    runtime = importlib.util.module_from_spec(runtime_spec)
    runtime_spec.loader.exec_module(runtime)
    return runtime, graph


def test_every_provider_phase_has_a_dependency_graph():
    runtime, graph = _load_modules()
    route = {"mode": "implement", "risk": "high"}
    phases = ("context", "research", "poc", "debug", "execute", "repair", "grill", "review")
    for phase in phases:
        team = runtime._phase_team(route, phase, (graph.AgentSpec, graph.GraphAgentTeam))
        assert len(team.agents) >= 4
        assert "planner" in team.agents
        assert "explorer" in team.agents
        assert "synthesizer" in team.agents
        assert team.levels()


def test_mutation_phases_have_serialized_builder_before_verifier():
    runtime, graph = _load_modules()
    route = {"mode": "implement", "risk": "low"}
    for phase in ("execute", "debug", "poc", "repair"):
        team = runtime._phase_team(route, phase, (graph.AgentSpec, graph.GraphAgentTeam))
        assert "builder" in team.agents
        assert "verifier" in team.agents
        assert "builder" in team.agents["verifier"].depends_on
        assert team.agents["builder"].read_only is False
        assert team.agents["verifier"].read_only is True


def test_high_risk_phases_add_security_and_architecture_review():
    runtime, graph = _load_modules()
    route = {"mode": "implement", "risk": "critical"}
    for phase in ("execute", "debug", "poc", "repair", "review", "grill"):
        team = runtime._phase_team(route, phase, (graph.AgentSpec, graph.GraphAgentTeam))
        assert "security-reviewer" in team.agents
        assert "architecture-reviewer" in team.agents
        assert "security-reviewer" in team.agents["synthesizer"].depends_on
        assert "architecture-reviewer" in team.agents["synthesizer"].depends_on
