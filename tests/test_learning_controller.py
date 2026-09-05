import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))

from learning_engine import Observation
from learning_controller import LearningController
from policy_registry import Policy, PolicyRegistry
from regression_replay import ReplayCase
from rollback_controller import PolicyHealth


class LearningControllerTests(unittest.TestCase):
    def test_promotion_changes_context_strategy_and_rollback_restores_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = PolicyRegistry([Policy("old", 1, "dotnet_bug", "history_first", "active", .88, .88, promoted_at=1)])
            controller = LearningController(Path(tmp), registry=registry)
            candidate = controller.learn_candidates([
                Observation(str(i), "dotnet_bug", "targeted_context", True, True, True) for i in range(3)
            ])[0]
            cases = [ReplayCase("r1", "dotnet_bug", True), ReplayCase("r2", "dotnet_bug", True), ReplayCase("r3", "dotnet_bug", True)]
            promoted = controller.evaluate_and_promote(candidate, cases, lambda _case, _candidate: (True, True), now=2)
            self.assertIsNotNone(promoted)
            self.assertEqual(controller.active_strategy("dotnet_bug"), "targeted_context")
            self.assertTrue(controller.monitor(PolicyHealth(candidate.policy_id, .95, .80, .02, .09), now=3))
            self.assertEqual(controller.active_strategy("dotnet_bug"), "history_first")

    def test_failed_replay_is_never_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = LearningController(Path(tmp))
            candidate = controller.learn_candidates([
                Observation(str(i), "bug", "strategy", True, True, True) for i in range(3)
            ])[0]
            cases = [ReplayCase("r1", "bug", True), ReplayCase("r2", "bug", True), ReplayCase("r3", "bug", True)]
            promoted = controller.evaluate_and_promote(candidate, cases, lambda case, _candidate: (case.case_id == "r1", True))
            self.assertIsNone(promoted)
            self.assertIsNone(controller.active_strategy("bug"))

    def test_promotion_requires_shadow_and_canary(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = LearningController(Path(tmp))
            candidate = controller.learn_candidates([
                Observation(str(i), "bug", "strategy", True, True, True) for i in range(3)
            ])[0]
            result = controller.replay_candidate(candidate, [ReplayCase("r1", "bug", True)], lambda _case, _candidate: (True, True))
            self.assertIsNone(controller.promote(candidate, result))


if __name__ == "__main__":
    unittest.main()
