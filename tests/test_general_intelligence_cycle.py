import tempfile
import unittest
from pathlib import Path

from portable.general_intelligence_cycle import GeneralIntelligenceCycle
from portable.persistent_memory import PersistentMemory
from portable.world_mega_model import WorldMegaModel
from portable.world_model import Observation


class GeneralIntelligenceCycleTests(unittest.TestCase):
    def test_perceive_plan_authorized_execute_and_learn(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = PersistentMemory(Path(tmp) / "memory.sqlite3", require_approval=False)
            model = WorldMegaModel(memory, "gi-demo")
            cycle = GeneralIntelligenceCycle(model)
            calls = []

            def executor(proposal):
                calls.append(proposal)
                return {"ok": True}

            result = cycle.run(
                cycle_id="cycle-1",
                intent="solve task",
                observation=Observation(
                    "obs-1", "task-1", "state", {"ready": True}, "test",
                    evidence=("e-1",),
                ),
                executor=executor,
                capability="reasoning",
                task_family="reasoning",
                learning_detail="verified successful execution",
                evidence_ids=("e-1", "e-2"),
                verified=True,
            )

            self.assertTrue(result.accepted)
            self.assertEqual(result.next_action, "continue")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["cycle_id"], "cycle-1")
            self.assertIsNotNone(result.learning)
            self.assertEqual(result.learning.outcome, "accepted")

    def test_unverified_result_cannot_become_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = PersistentMemory(Path(tmp) / "memory.sqlite3", require_approval=False)
            model = WorldMegaModel(memory, "gi-demo")
            result = GeneralIntelligenceCycle(model).run(
                cycle_id="cycle-2",
                intent="inspect",
                observation=Observation(
                    "obs-2", "task-2", "state", "unknown", "test",
                ),
                executor=lambda proposal: {"ok": False},
                learning_detail="unverified outcome",
                evidence_ids=("e-3",),
                verified=False,
            )
            self.assertFalse(result.accepted)
            self.assertEqual(result.next_action, "verify")
            self.assertIsNotNone(result.learning)
            self.assertFalse(result.learning.verified)


if __name__ == "__main__":
    unittest.main()
