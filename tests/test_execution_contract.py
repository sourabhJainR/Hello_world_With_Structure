from __future__ import annotations
import unittest
from portable.execution_contract import EvidenceReference, ExecutionEnvelope, ExecutionIntent, ExecutionPlanRef, RepositoryReference

class ExecutionContractTests(unittest.TestCase):
    def envelope(self, evidence=()):
        return ExecutionEnvelope(ExecutionIntent('task-1','change source'), RepositoryReference('repo-1'), ExecutionPlanRef('plan-1', ('task-1',)), tuple(evidence))

    def test_round_trip_and_digest_are_stable(self):
        envelope=self.envelope((EvidenceReference('e1','repo-1','current'),))
        self.assertEqual(ExecutionEnvelope.from_dict(envelope.to_dict()).digest, envelope.digest)

    def test_plan_must_contain_task(self):
        with self.assertRaises(ValueError):
            self.envelope().__class__(ExecutionIntent('task-1','change source'), RepositoryReference('repo-1'), ExecutionPlanRef('plan-1', ('other',))).validate()

    def test_evidence_snapshot_must_match_repository(self):
        with self.assertRaises(ValueError):
            self.envelope((EvidenceReference('e1','repo-2'),)).validate()

    def test_duplicate_evidence_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.envelope((EvidenceReference('e1','repo-1'), EvidenceReference('e1','repo-1'))).validate()

if __name__ == '__main__':
    unittest.main()
