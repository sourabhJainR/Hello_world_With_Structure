import tempfile
import unittest
from pathlib import Path

from portable.hypothesis_engine import BeliefEvidence, Hypothesis, HypothesisEngine
from portable.persistent_memory import PersistentMemory


class HypothesisEngineTests(unittest.TestCase):
    def test_support_and_contradiction_remain_separate_and_update_belief(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = HypothesisEngine(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            engine.propose(Hypothesis("h1", "why", "pool is exhausted", "test"))
            engine.add_evidence(BeliefEvidence("e1", "h1", True, "pool reached limit", "metric", 1.0,
                                               "2026-01-01T00:00:00+00:00"))
            engine.add_evidence(BeliefEvidence("e2", "h1", False, "failure also occurs at low usage", "trace", 0.5,
                                               "2026-01-02T00:00:00+00:00"))
            result = engine.assess("h1")
            self.assertAlmostEqual(result.confidence, 2 / 3, places=6)
            self.assertEqual(result.status, "inconclusive")
            self.assertEqual([item.supports for item in engine.evidence("h1")], [True, False])
            self.assertEqual(len(engine.digest("h1")), 16)

    def test_identity_collisions_and_missing_hypotheses_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = HypothesisEngine(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            hypothesis = Hypothesis("h1", "why", "x", "test", created_at="2026-01-01T00:00:00+00:00")
            engine.propose(hypothesis)
            engine.propose(hypothesis)
            with self.assertRaises(ValueError):
                engine.propose(Hypothesis("h1", "why", "different", "test", created_at="2026-01-01T00:00:00+00:00"))
            with self.assertRaises(KeyError):
                engine.add_evidence(BeliefEvidence("e1", "missing", True, "x", "test"))

    def test_validation_rejects_naive_timestamp_and_invalid_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            Hypothesis("h1", "q", "s", "test", created_at="2026-01-01T00:00:00")
        with self.assertRaisesRegex(ValueError, "status"):
            Hypothesis("h1", "q", "s", "test", status="unknown")


if __name__ == "__main__":
    unittest.main()
