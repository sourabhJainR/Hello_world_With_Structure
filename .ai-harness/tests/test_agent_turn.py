import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.agent_turn import AgentTurnStateMachine, estimate_tokens


class AgentTurnTests(unittest.TestCase):
    def test_tool_usage_cache_and_lineage_are_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            turn = AgentTurnStateMachine("execute", run_dir, "execute-1")
            turn.transition("planning")
            turn.transition("acting")
            turn.set_context(["repo:abc", "memory:def"], "ctx123")
            output = "\n".join([
                'HARNESS_TOOL_OBSERVATION:{"sequence":1,"tool":"shell","status":"success","duration_ms":12,"result":"tests passed"}',
                'HARNESS_USAGE:{"input_tokens":100,"output_tokens":40,"cached_input_tokens":60,"total_tokens":140}',
                'HARNESS_CACHE:{"hit":true,"read_tokens":60,"cache_key":"ctx123","source":"provider"}',
            ])
            turn.observe_tools(output)
            turn.observe_usage("prompt", output)
            turn.observe_cache(output, "ctx123")
            self.assertEqual(turn.turn.observations[0].tool, "shell")
            self.assertEqual(turn.turn.usage.total_tokens, 140)
            self.assertTrue(turn.turn.cache.hit)
            self.assertEqual(turn.turn.context_pages, ["repo:abc", "memory:def"])
            self.assertTrue((run_dir / "agent-turns.jsonl").exists())

    def test_decision_is_measurable(self):
        with tempfile.TemporaryDirectory() as tmp:
            turn = AgentTurnStateMachine("validate", Path(tmp), "validate-1")
            turn.transition("planning")
            turn.transition("acting")
            turn.observe_tools('HARNESS_TOOL_OBSERVATION:{"tool":"pytest","status":"success"}')
            turn.observe_usage("x" * 100, "y" * 100)
            turn.transition("observing")
            turn.transition("verifying")
            decision = turn.decide(verification_score=1.0, evidence_score=1.0, uncertainty=0.0)
            self.assertEqual(decision["action"], "stop")
            turn.transition("deciding")
            turn.finish("completed")
            self.assertEqual(turn.turn.state, "completed")

    def test_estimated_tokens_are_deterministic(self):
        self.assertEqual(estimate_tokens("12345678"), 2)


if __name__ == "__main__":
    unittest.main()
