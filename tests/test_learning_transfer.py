import tempfile
import unittest
from pathlib import Path

from portable.learning_transfer import LearningExperience, LearningTransfer
from portable.persistent_memory import PersistentMemory


class LearningTransferTests(unittest.TestCase):
    def test_verified_learning_transfers_across_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            learning = LearningTransfer(memory, "target")
            learning.record(
                LearningExperience("e1", "source-a", "api-migration", "python", "worked", "Use bounded batches", ("ev1",), 0.9, True)
            )
            learning.record(
                LearningExperience("e2", "source-b", "api-migration", "python", "worked", "Use bounded batches", ("ev2",), 0.8, True)
            )
            candidates = learning.transfer("api-migration", "python", limit=5)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].detail, "Use bounded batches")
            self.assertEqual(candidates[0].source_projects, ("source-a", "source-b"))

    def test_structural_transfer_finds_related_verified_experience(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            learning = LearningTransfer(memory, "target")
            learning.record(LearningExperience(
                "e1", "source-a", "parser", "recovery", "worked", "retry after timeout",
                ("ev1",), 0.9, True, ("retry", "timeout"),
            ))
            candidates = learning.transfer_structural("parser", "recovery", ("retry", "timeout", "backoff"))
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].detail, "retry after timeout")
            self.assertGreater(candidates[0].similarity, 0.5)

    def test_structural_transfer_rejects_negative_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            learning = LearningTransfer(memory, "target")
            learning.record(LearningExperience(
                "e1", "source-a", "parser", "recovery", "worked", "retry safely",
                ("ev1",), 0.9, True, ("retry", "timeout"), ("non_idempotent_action",),
            ))
            self.assertEqual(
                learning.transfer_structural(
                    "parser", "recovery", ("retry", "timeout"),
                    target_conditions=("non_idempotent_action",),
                ), []
            )

    def test_consolidation_requires_independent_verified_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            learning = LearningTransfer(memory, "target")
            learning.record(LearningExperience("e1", "source-a", "debugging", "terminal", "worked", "Check root cause first", ("a",), 0.9, True))
            learning.record(LearningExperience("e2", "source-a", "debugging", "terminal", "worked", "Check root cause first", ("b",), 0.95, True))
            self.assertIsNone(learning.consolidate("debugging", "terminal", min_projects=2))
            learning.record(LearningExperience("e3", "source-b", "debugging", "terminal", "worked", "Check root cause first", ("c",), 0.85, True))
            receipt = learning.consolidate("debugging", "terminal", min_projects=2)
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(receipt.source_projects, ("source-a", "source-b"))
            recalled = memory.search("target", "Check root cause first")
            self.assertEqual(len(recalled), 1)
            self.assertTrue(recalled[0].verified)

    def test_failures_and_unverified_experiences_do_not_become_transferable_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            learning = LearningTransfer(memory, "target")
            learning.record(LearningExperience("e1", "source-a", "deploy", "terminal", "failed", "Disable checks", ("a",), 0.9, True))
            learning.record(LearningExperience("e2", "source-b", "deploy", "terminal", "worked", "Skip verification", ("b",), 0.9, False))
            self.assertEqual(learning.transfer("deploy", "terminal"), [])
            self.assertIsNone(learning.consolidate("deploy", "terminal", min_projects=2))

    def test_verified_learning_requires_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            learning = LearningTransfer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "target")
            with self.assertRaises(ValueError):
                learning.record(LearningExperience("e1", "source-a", "task", "cap", "worked", "detail", (), 0.8, True))

    def test_duplicate_experience_id_must_be_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            learning = LearningTransfer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "target")
            experience = LearningExperience("e1", "source-a", "task", "cap", "worked", "detail", (), 0.8, False)
            learning.record(experience)
            learning.record(experience)
            with self.assertRaises(ValueError):
                learning.record(LearningExperience("e1", "source-b", "task", "cap", "worked", "other", (), 0.8, False))


if __name__ == "__main__":
    unittest.main()
