import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))

from learning_engine import Observation, learn
from policy_registry import Policy, PolicyRegistry
from regression_replay import ReplayCase, replay
from rollback_controller import PolicyHealth, should_rollback


class LearningEngineTests(unittest.TestCase):
    def test_learns_repeated_verified_strategy(self):
        rows = [Observation(str(i), "dotnet_bug", "targeted_context", True, True, True) for i in range(3)]
        candidates = learn(rows)
        self.assertEqual(len(candidates), 1)
        self.assertGreaterEqual(candidates[0].confidence, 0.8)

    def test_replay_detects_regression(self):
        cases = [ReplayCase("a", "bug", True), ReplayCase("b", "bug", True)]
        result = replay(cases, lambda c: (c.case_id == "a", True))
        self.assertFalse(result.passed)
        self.assertEqual(result.failures, ("b",))

    def test_registry_promote_and_rollback(self):
        registry = PolicyRegistry()
        registry.add_candidate(Policy("p", 1, "bug", "strategy", confidence=0.9))
        registry.promote("p", 1, now=10)
        self.assertEqual(registry.active("bug")[0].status, "active")
        registry.rollback("p", 1, now=20)
        self.assertEqual(registry.active("bug"), [])

    def test_health_threshold(self):
        self.assertTrue(should_rollback(PolicyHealth("p", .9, .75, .02, .09)))
        self.assertFalse(should_rollback(PolicyHealth("p", .9, .85, .02, .04)))


if __name__ == "__main__":
    unittest.main()
