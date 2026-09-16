import tempfile
import unittest
from pathlib import Path

from portable.generalization import Abstraction, GeneralizationEngine
from portable.persistent_memory import PersistentMemory


class GeneralizationTests(unittest.TestCase):
    def _engine(self, directory: str) -> GeneralizationEngine:
        memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
        return GeneralizationEngine(memory, "target")

    def test_structural_analogy_ranks_overlap_and_preserves_negative_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self._engine(directory)
            engine.record(Abstraction(
                "a1", "retry-with-backoff", "network recovery",
                frozenset({"retry", "timeout", "backoff"}), ("e1",), 0.9,
                frozenset({"non_idempotent_action"}),
            ))
            candidate = engine.find_analogies(frozenset({"retry", "timeout", "backoff"}), limit=5)[0]
            self.assertEqual(candidate.abstraction_id, "a1")
            self.assertEqual(candidate.similarity, 1.0)
            self.assertIn("non_idempotent_action", candidate.negative_conditions)

    def test_validation_requires_independent_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self._engine(directory)
            engine.record(Abstraction(
                "a1", "parser-recovery", "recovery",
                frozenset({"retry", "validate"}), ("e1",), 0.8, frozenset(),
            ))
            candidate = engine.find_analogies(frozenset({"retry", "validate"}))[0]
            self.assertFalse(engine.validate_candidate(candidate, evidence_ids=()))
            self.assertFalse(engine.validate_candidate(candidate, evidence_ids=("e1",)))
            self.assertTrue(engine.validate_candidate(candidate, evidence_ids=("e2",)))

    def test_candidates_conflicting_with_target_conditions_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self._engine(directory)
            engine.record(Abstraction(
                "safe", "recovery", "debug", frozenset({"retry"}), ("e1",), 0.8, frozenset(),
            ))
            engine.record(Abstraction(
                "unsafe", "recovery", "debug", frozenset({"retry"}), ("e2",), 0.95,
                frozenset({"non_idempotent_action"}),
            ))
            candidates = engine.find_analogies(
                frozenset({"retry"}), target_conditions=frozenset({"non_idempotent_action"}), limit=5,
            )
            self.assertEqual([candidate.abstraction_id for candidate in candidates], ["safe"])


if __name__ == "__main__":
    unittest.main()
