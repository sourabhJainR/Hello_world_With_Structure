import tempfile
import unittest
from pathlib import Path

from portable.capability_acquisition import CapabilityAcquirer, CapabilityNeed, PracticeResult
from portable.persistent_memory import PersistentMemory
from portable.skill_graph import SkillGraph


class CapabilityAcquisitionTests(unittest.TestCase):
    def _acquirer(self, directory: str) -> CapabilityAcquirer:
        return CapabilityAcquirer(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")

    def _proposal(self, acquirer: CapabilityAcquirer):
        return acquirer.propose(CapabilityNeed("parser", "recovery", 3, ("gap-1", "gap-2", "gap-3"), True))

    def test_practice_records_bounded_success(self):
        with tempfile.TemporaryDirectory() as directory:
            acquirer = self._acquirer(directory)
            proposal = self._proposal(acquirer)
            assert proposal is not None
            result = acquirer.practice(proposal.id, lambda: {"tests_passed": True, "safety_reviewed": True, "detail": "sandbox pass"})
            self.assertTrue(result.accepted)
            self.assertTrue(result.tests_passed)
            self.assertTrue(result.safety_reviewed)

    def test_practice_failure_is_recorded_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            acquirer = self._acquirer(directory)
            proposal = self._proposal(acquirer)
            assert proposal is not None
            result = acquirer.practice(proposal.id, lambda: (_ for _ in ()).throw(RuntimeError("sandbox failed")))
            self.assertFalse(result.accepted)
            self.assertIn("sandbox failed", result.error or "")

    def test_graduation_requires_repeated_success_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            acquirer = self._acquirer(directory)
            proposal = self._proposal(acquirer)
            assert proposal is not None
            first = acquirer.practice(proposal.id, lambda: {"tests_passed": True, "safety_reviewed": True})
            receipt = acquirer.graduate(proposal.id, (first,), evidence_ids=("practice-1",))
            self.assertFalse(receipt.accepted)
            second = acquirer.practice(proposal.id, lambda: {"tests_passed": True, "safety_reviewed": True})
            receipt = acquirer.graduate(proposal.id, (first, second), evidence_ids=("practice-1", "practice-2"))
            self.assertTrue(receipt.accepted)
            self.assertEqual(receipt.practice_attempts, (first.attempt_id, second.attempt_id))

            graph = SkillGraph(acquirer.memory, "project-x")
            self.assertTrue(graph.ready("recovery"))

    def test_graduation_rejects_fabricated_practice_results(self):
        with tempfile.TemporaryDirectory() as directory:
            acquirer = self._acquirer(directory)
            proposal = self._proposal(acquirer)
            assert proposal is not None
            fabricated = (
                PracticeResult(proposal.id, "fake-1", True, True, True),
                PracticeResult(proposal.id, "fake-2", True, True, True),
            )
            receipt = acquirer.graduate(proposal.id, fabricated, evidence_ids=("e1", "e2"))
            self.assertFalse(receipt.accepted)
            self.assertIn("persisted accepted attempts", receipt.reasons[0])


if __name__ == "__main__":
    unittest.main()
