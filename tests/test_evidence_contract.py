"""Regression tests for the canonical evidence spine."""
from __future__ import annotations
import unittest
from portable.evidence_contract import EvidenceClaim, EvidenceSpine, evidence_from_state

class EvidenceContractTests(unittest.TestCase):
    def claim(self, evidence_id: str = "e1", snapshot: str = "repo-1") -> EvidenceClaim:
        return EvidenceClaim(evidence_id, "source", "repo", "Observed source fact", "high", "src/example.py:1", snapshot, "current", "repository-model")

    def test_requires_snapshot_and_provenance(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceClaim("e1", "source", "repo", "fact", "high").validate()

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceSpine([self.claim(), self.claim()])

    def test_references_must_exist_and_match_snapshot(self) -> None:
        spine = EvidenceSpine([self.claim()])
        with self.assertRaises(ValueError):
            spine.validate_references([type("Ref", (), {"evidence_id": "missing", "snapshot": "repo-1"})()], repository_snapshot="repo-1")
        with self.assertRaises(ValueError):
            spine.validate_references([type("Ref", (), {"evidence_id": "e1", "snapshot": "repo-2"})()], repository_snapshot="repo-1")

    def test_state_records_round_trip_into_spine(self) -> None:
        spine = evidence_from_state([self.claim().__dict__])
        self.assertEqual(spine.require("e1").claim, "Observed source fact")

if __name__ == "__main__":
    unittest.main()
