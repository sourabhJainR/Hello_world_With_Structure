import tempfile
import unittest
from pathlib import Path

from portable.continual_learning import BenchmarkObservation, ContinualLearningGuard
from portable.persistent_memory import PersistentMemory


class ContinualLearningTests(unittest.TestCase):
    def test_baseline_then_regression_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            guard = ContinualLearningGuard(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            baseline = guard.record(BenchmarkObservation("suite", "reasoning", "v1", 0.90, 10, ("e1",), True))
            self.assertTrue(baseline.accepted)
            result = guard.compare(BenchmarkObservation("suite", "reasoning", "v2", 0.82, 10, ("e2",), True), tolerance=0.05)
            self.assertFalse(result.accepted)
            self.assertTrue(result.regressed)
            self.assertLess(result.delta, -0.05)

    def test_non_regression_is_accepted_and_history_is_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.db"
            guard = ContinualLearningGuard(PersistentMemory(path, require_approval=False), "demo")
            guard.record(BenchmarkObservation("suite", "transfer", "v1", 0.70, 10, ("e1",), True))
            result = guard.compare(BenchmarkObservation("suite", "transfer", "v2", 0.71, 12, ("e2",), True), tolerance=0.05)
            self.assertTrue(result.accepted)
            self.assertFalse(result.regressed)
            reopened = ContinualLearningGuard(PersistentMemory(path, require_approval=False), "demo")
            self.assertEqual(reopened.history("suite", "transfer"), guard.history("suite", "transfer"))

    def test_missing_evidence_and_invalid_tolerance_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            guard = ContinualLearningGuard(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            with self.assertRaises(ValueError):
                guard.record(BenchmarkObservation("suite", "reasoning", "v1", 0.9, 1, (), True))
            with self.assertRaises(ValueError):
                guard.compare(BenchmarkObservation("suite", "reasoning", "v1", 0.9, 1, ("e",), True), tolerance=-0.1)


if __name__ == "__main__":
    unittest.main()
