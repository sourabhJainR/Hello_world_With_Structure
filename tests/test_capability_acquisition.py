import tempfile
import unittest
from pathlib import Path

from portable.capability_acquisition import CapabilityAcquirer, CapabilityNeed, ValidationEvidence
from portable.persistent_memory import PersistentMemory


class CapabilityAcquisitionTests(unittest.TestCase):
    def test_repeated_verified_need_creates_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            acquirer = CapabilityAcquirer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            need = CapabilityNeed("data-extract", "spreadsheet", 3, ("e1", "e2", "e3"), True)
            proposal = acquirer.propose(need)
            self.assertIsNotNone(proposal)
            assert proposal is not None
            self.assertEqual(proposal.capability, "spreadsheet")
            self.assertEqual(proposal.missing_count, 3)
            self.assertFalse(proposal.executable)

    def test_sparse_or_unverified_need_is_not_proposed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            acquirer = CapabilityAcquirer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            self.assertIsNone(acquirer.propose(CapabilityNeed("task", "browser", 1, ("e1",), True)))
            self.assertIsNone(acquirer.propose(CapabilityNeed("task", "browser", 4, ("e1",), False)))

    def test_validation_requires_evidence_tests_and_safety_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            acquirer = CapabilityAcquirer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            proposal = acquirer.propose(CapabilityNeed("task", "parser", 4, ("e1", "e2", "e3", "e4"), True))
            assert proposal is not None
            rejected = acquirer.validate(proposal.id, ValidationEvidence((), True, True))
            self.assertFalse(rejected.accepted)
            accepted = acquirer.validate(proposal.id, ValidationEvidence(("v1", "v2"), True, True))
            self.assertTrue(accepted.accepted)
            self.assertFalse(accepted.executable)

    def test_unknown_proposal_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            acquirer = CapabilityAcquirer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            with self.assertRaises(KeyError):
                acquirer.validate("missing", ValidationEvidence(("v1",), True, True))


if __name__ == "__main__":
    unittest.main()
