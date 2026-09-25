import tempfile
import unittest
from pathlib import Path

from portable.capability_acquisition import CapabilityAcquirer
from portable.capability_evolution import CapabilityEvolution
from portable.persistent_memory import PersistentMemory


class CapabilityEvolutionTests(unittest.TestCase):
    def _router(self, root: Path) -> CapabilityEvolution:
        memory = PersistentMemory(root / "memory.db", require_approval=False)
        return CapabilityEvolution(CapabilityAcquirer(memory, "demo"))

    def test_repeated_verified_gap_creates_bounded_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            router = self._router(Path(directory))
            result = router.evaluate(
                "browser-research",
                "citation-extraction",
                [
                    {"outcome": "failed", "verified": True, "evidence_ids": ("e1",)},
                    {"outcome": "failed", "verified": True, "evidence_ids": ("e2",)},
                    {"outcome": "regressed", "verified": True, "evidence_ids": ("e3",)},
                ],
            )
            self.assertEqual(result.status, "propose")
            self.assertIsNotNone(result.proposal)
            self.assertEqual(result.proposal.capability, "citation-extraction")
            self.assertFalse(result.proposal.executable)

    def test_sparse_or_unverified_history_only_observes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            router = self._router(Path(directory))
            result = router.evaluate(
                "browser-research",
                "citation-extraction",
                [
                    {"outcome": "failed", "verified": True, "evidence_ids": ("e1",)},
                    {"outcome": "failed", "verified": False, "evidence_ids": ("e2",)},
                ],
            )
            self.assertEqual(result.status, "observe")
            self.assertIsNone(result.proposal)

    def test_successes_do_not_trigger_acquisition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            router = self._router(Path(directory))
            result = router.evaluate(
                "browser-research",
                "citation-extraction",
                [
                    {"outcome": "worked", "verified": True, "evidence_ids": ("e1", "e2", "e3")},
                    {"outcome": "worked", "verified": True, "evidence_ids": ("e4",)},
                    {"outcome": "worked", "verified": True, "evidence_ids": ("e5",)},
                ],
            )
            self.assertEqual(result.status, "observe")


if __name__ == "__main__":
    unittest.main()
