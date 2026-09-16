import tempfile
import unittest
from pathlib import Path

from portable.cognitive_learning import BeliefContext, CognitiveLearningLoop
from portable.cognitive_runtime import CognitiveRuntime
from portable.persistent_memory import PersistentMemory
from portable.self_model import SelfModel


class CognitiveLearningTests(unittest.TestCase):
    def test_beliefs_are_ranked_by_uncertainty(self):
        beliefs = (
            BeliefContext("b2", "parser may be slow", 0.8, ("e2",)),
            BeliefContext("b1", "parser may fail", 0.2, ("e1",)),
        )
        selected = CognitiveLearningLoop.select_beliefs(beliefs, limit=1)
        self.assertEqual(tuple(item.belief_id for item in selected), ("b1",))

    def test_learning_signal_is_persisted_and_updates_self_model(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            loop = CognitiveLearningLoop(memory, "project-x")
            signal = loop.record(task_id="t1", intent="fix parser", status="accepted", capability="parser", evidence=("ev1",), context="repo")
            self.assertEqual(signal.status, "accepted")
            self.assertTrue(signal.digest)
            profile = SelfModel(memory, "project-x").profile("parser", context="repo")
            self.assertEqual(profile.confidence, 1.0)
            self.assertEqual(profile.observations, 1)

    def test_learning_persistence_failure_isolated(self):
        class BrokenMemory(PersistentMemory):
            def _connect(self):
                raise RuntimeError("forced learning failure")

        with tempfile.TemporaryDirectory() as directory:
            memory = BrokenMemory(Path(directory) / "memory.db", require_approval=False)
            with self.assertRaises(RuntimeError):
                CognitiveRuntime.create(memory, "project-x")
            # The learning loop itself must surface the isolated diagnostic object rather than raising.
            loop = object.__new__(CognitiveLearningLoop)
            loop.memory = memory
            loop.project = "project-x"
            loop.self_model = None
            loop.max_signals = 10
            signal = CognitiveLearningLoop.record(loop, task_id="t1", intent="fix", status="failed")
            self.assertTrue(signal.persistence_errors)


if __name__ == "__main__":
    unittest.main()
