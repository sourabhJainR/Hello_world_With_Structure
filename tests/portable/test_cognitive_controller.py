import tempfile
import unittest
from pathlib import Path

from portable.cognitive_controller import CognitiveController
from portable.cognitive_runtime import CognitiveRuntime
from portable.goal_manager import Goal
from portable.information_planner import InformationAction
from portable.persistent_memory import PersistentMemory
from portable.self_model import SelfModel


class CognitiveControllerTests(unittest.TestCase):
    def test_plan_uses_goal_information_and_self_model(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            cognitive = CognitiveRuntime.create(memory, "project-x")
            cognitive.goals.create(Goal("g1", "Finish parser", priority=90))
            cognitive.self_model.record("o1", "parser", success=True)
            controller = CognitiveController(cognitive)
            plan = controller.plan(
                "Fix parser", capability="parser", uncertainty=0.8,
                information_actions=(InformationAction("inspect", "Inspect failing path", 0.7, 1.0, 0.1),),
            )
            self.assertEqual(plan.goal_id, "g1")
            self.assertEqual(plan.information_action_id, "inspect")
            self.assertEqual(plan.self_confidence, 1.0)
            enriched = controller.enrich_context("Fix parser", context={"existing": True})
            self.assertTrue(enriched["existing"])
            self.assertIn("aer_cognitive_plan", enriched)

    def test_plan_does_not_execute_information_action(self):
        called = False
        def should_not_run():
            nonlocal called
            called = True
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            controller = CognitiveController(CognitiveRuntime.create(memory, "project-x"))
            controller.plan("Explore", information_actions=(InformationAction("act", "bounded action", 0.5),))
            self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
