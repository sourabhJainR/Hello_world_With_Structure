from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from portable.local_offload import ResourceBudget


MODULE = Path(__file__).resolve().parents[1] / ".ai-harness" / "runtime" / "graph_agent_team.py"
SPEC = importlib.util.spec_from_file_location("aer_graph_agent_team", MODULE)
GRAPH_TEAM = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = GRAPH_TEAM
SPEC.loader.exec_module(GRAPH_TEAM)


class GraphResourceExecutionTests(unittest.TestCase):
    def test_read_only_deterministic_work_selects_local_lane(self):
        team = GRAPH_TEAM.GraphAgentTeam(
            [GRAPH_TEAM.AgentSpec("verifier", "verifier", local_command=("python", "-c", "print('ok')"))],
            resource_budget=ResourceBudget(max_workers=1, timeout_seconds=10),
        )
        decision = team._resource_decision(team.agents["verifier"])
        self.assertEqual(decision.lane, "local")
        self.assertEqual(decision.command[:2], ("python", "-c"))

    def test_mutating_agent_stays_on_agent_lane(self):
        team = GRAPH_TEAM.GraphAgentTeam(
            [GRAPH_TEAM.AgentSpec("builder", "builder", read_only=False, local_command=("python", "-c", "print('ok')"))],
            resource_budget=ResourceBudget(max_workers=1, timeout_seconds=10),
        )
        decision = team._resource_decision(team.agents["builder"])
        self.assertEqual(decision.lane, "agent")

    def test_local_result_is_bounded_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = GRAPH_TEAM.SharedTaskMemory(root / "state" / "memory.jsonl", "digest")
            team = GRAPH_TEAM.GraphAgentTeam(
                [GRAPH_TEAM.AgentSpec("verifier", "verifier", local_command=("python", "-c", "print('ok')"))],
                resource_budget=ResourceBudget(max_workers=1, timeout_seconds=10),
            )
            decision = team._resource_decision(team.agents["verifier"])
            result = team._run_local(team.agents["verifier"], decision, memory)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.status, "passed")
            self.assertIn("ok", result.output)


if __name__ == "__main__":
    unittest.main()
