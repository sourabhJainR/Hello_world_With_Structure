from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / ".ai-harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from runtime import _phase_team
from runtime.graph_agent_team import AgentSpec, GraphAgentTeam


def test_every_provider_phase_has_a_dependency_graph():
    route = {"mode": "implement", "risk": "high"}
    phases = ("context", "research", "poc", "debug", "execute", "repair", "grill", "review")
    for phase in phases:
        team = _phase_team(route, phase, (AgentSpec, GraphAgentTeam))
        assert len(team.agents) >= 4
        assert "planner" in team.agents
        assert "explorer" in team.agents
        assert "synthesizer" in team.agents
        assert team.levels()


def test_mutation_phases_have_serialized_builder_before_verifier():
    route = {"mode": "implement", "risk": "low"}
    for phase in ("execute", "debug", "poc", "repair"):
        team = _phase_team(route, phase, (AgentSpec, GraphAgentTeam))
        assert "builder" in team.agents
        assert "verifier" in team.agents
        assert "builder" in team.agents["verifier"].depends_on
        assert team.agents["builder"].read_only is False
        assert team.agents["verifier"].read_only is True


def test_high_risk_phases_add_security_and_architecture_review():
    route = {"mode": "implement", "risk": "critical"}
    for phase in ("execute", "debug", "poc", "repair", "review", "grill"):
        team = _phase_team(route, phase, (AgentSpec, GraphAgentTeam))
        assert "security-reviewer" in team.agents
        assert "architecture-reviewer" in team.agents
        assert "security-reviewer" in team.agents["synthesizer"].depends_on
        assert "architecture-reviewer" in team.agents["synthesizer"].depends_on
