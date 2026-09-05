import tempfile
import unittest
from pathlib import Path

from runtime.graph_agent_team import AgentSpec, GraphAgentTeam, SharedTaskMemory, team_for_route


class GraphAgentTeamTests(unittest.TestCase):
    def test_shared_memory_is_scoped_to_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.jsonl"
            first = SharedTaskMemory(path, "intent-a")
            second = SharedTaskMemory(path, "intent-b")
            first.publish(agent="planner", role="planner", kind="fact", text="only task A", confidence=1.0)
            self.assertEqual(len(first.snapshot()), 1)
            self.assertEqual(second.snapshot(), [])

    def test_dependency_levels_and_parallel_read_only_roles(self):
        team = GraphAgentTeam([
            AgentSpec("planner", "planner"),
            AgentSpec("explorer", "explorer", depends_on=("planner",)),
            AgentSpec("researcher", "researcher", depends_on=("planner",)),
            AgentSpec("builder", "builder", depends_on=("explorer", "researcher"), read_only=False),
        ])
        levels = [[agent.name for agent in level] for level in team.levels()]
        self.assertEqual(levels[0], ["planner"])
        self.assertEqual(set(levels[1]), {"explorer", "researcher"})
        self.assertEqual(levels[2], ["builder"])

    def test_team_passes_shared_memory_to_downstream_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = SharedTaskMemory(Path(tmp) / "memory.jsonl", "intent-a")
            seen = {}

            def invoke(agent, prompt):
                seen[agent.name] = prompt
                return 0, f"finding from {agent.name}", 0.01

            team = GraphAgentTeam([
                AgentSpec("planner", "planner"),
                AgentSpec("builder", "builder", depends_on=("planner",), read_only=False),
            ])
            result = team.execute(task="implement X", intent_digest="intent-a", base_prompt="base", memory=memory, invoke_agent=invoke)
            self.assertTrue(result["accepted"])
            self.assertIn("finding from planner", seen["builder"])
            self.assertEqual(result["shared_memory_entries"], 2)

    def test_route_creates_builder_verifier_and_reviews(self):
        team = team_for_route({"mode": "implement", "capabilities": [], "risk": "high"})
        names = set(team.agents)
        self.assertTrue({"planner", "explorer", "builder", "verifier", "correctness-reviewer", "security-reviewer", "architecture-reviewer", "synthesizer"}.issubset(names))

    def test_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            GraphAgentTeam([
                AgentSpec("a", "a", depends_on=("b",)),
                AgentSpec("b", "b", depends_on=("a",)),
            ])


if __name__ == "__main__":
    unittest.main()
