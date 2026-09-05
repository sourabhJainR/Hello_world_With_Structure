from pathlib import Path
import tempfile
import unittest

from ai_harness.runtime.regression_memory import RegressionKnowledge, RegressionMemory


class RegressionMemoryTests(unittest.TestCase):
    def test_unverified_knowledge_is_not_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = RegressionMemory(Path(tmp) / "regression.db")
            item = RegressionKnowledge("", "bug", component="orchestration", failure_signature="side-effect", invariant="candidate-not-executed", confidence=0.95, test_pointer="tests/test_x.py", evidence_pointer="run-1")
            memory.record(item, verified=False)
            self.assertEqual(memory.retrieve(task_family="bug"), [])
            self.assertEqual(memory.stats(), {"total": 1, "active": 0, "pending": 1})

    def test_verified_knowledge_is_retrieved_and_ranked_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = RegressionMemory(Path(tmp) / "regression.db")
            exact = RegressionKnowledge("", "story", component="orchestration", failure_signature="candidate-not-executed", invariant="no-import-execution", confidence=0.95, test_pointer="tests/test_x.py", evidence_pointer="run-2")
            family = RegressionKnowledge("family", "story", component="planner", invariant="bounded-context", confidence=0.90, test_pointer="tests/test_y.py", evidence_pointer="run-3")
            memory.record(exact, verified=True)
            memory.record(family, verified=True)
            rows = memory.retrieve(task_family="story", component="orchestration", failure_signature="candidate-not-executed", invariant="no-import-execution")
            self.assertEqual(rows[0].failure_signature, "candidate-not-executed")
            self.assertEqual(memory.stats(), {"total": 2, "active": 2, "pending": 0})


if __name__ == "__main__":
    unittest.main()
