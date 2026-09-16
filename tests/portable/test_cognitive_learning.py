import tempfile
import unittest
from pathlib import Path

from portable.cognitive_learning import BeliefContext, CognitiveLearningLoop
from portable.cognitive_runtime import CognitiveRuntime
from portable.hypothesis_engine import BeliefEvidence, Hypothesis
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

    def test_persisted_hypotheses_become_bounded_belief_context(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            runtime = CognitiveRuntime.create(memory, "project-x")
            runtime.hypotheses.propose(Hypothesis("h2", "q", "less certain", "test", confidence=0.8))
            runtime.hypotheses.propose(Hypothesis("h1", "q", "more uncertain", "test", confidence=0.2))
            loop = CognitiveLearningLoop(memory, "project-x", self_model=runtime.self_model)
            selected = loop.beliefs(limit=2)
            self.assertEqual(tuple(item.belief_id for item in selected), ("h1", "h2"))

    def test_belief_evidence_updates_hypothesis_after_learning_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            runtime = CognitiveRuntime.create(memory, "project-x")
            runtime.hypotheses.propose(Hypothesis("h1", "q", "statement", "test", confidence=0.5))
            loop = CognitiveLearningLoop(memory, "project-x", self_model=runtime.self_model)
            signal = loop.record(
                task_id="t1", intent="task", status="accepted", evidence=("ev1",),
                belief_evidence=(BeliefEvidence("be1", "h1", True, "observed success", "runtime", 0.9),),
            )
            self.assertFalse(signal.persistence_errors)
            self.assertEqual(runtime.hypotheses.assess("h1").confidence, 1.0)

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
            loop = object.__new__(CognitiveLearningLoop)
            loop.memory = memory
            loop.project = "project-x"
            loop.self_model = None
            loop.hypotheses = None
            loop.max_signals = 10
            signal = CognitiveLearningLoop.record(loop, task_id="t1", intent="fix", status="failed")
            self.assertTrue(signal.persistence_errors)


if __name__ == "__main__":
    unittest.main()
