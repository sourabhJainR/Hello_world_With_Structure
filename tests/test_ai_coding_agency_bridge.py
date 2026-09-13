import tempfile
import unittest
from pathlib import Path

from portable.agency_artifact_regression import snapshot_artifact
from portable.ai_coding_agency_bridge import CodingTask, run_coding_task, verify_provenance


class AICodingAgencyBridgeTests(unittest.TestCase):
    def _worker(self, task, assignments):
        return {
            "deliverables": ["implemented change"],
            "verification": ["focused tests passed"],
            "dimensions": {
                "correctness": 25,
                "completeness": 15,
                "evidence": 15,
                "verification": 15,
                "scope_discipline": 10,
                "security_and_safety": 10,
                "clarity": 5,
                "maintainability": 5,
            },
            "hard_gates": {
                "acceptance_criteria_satisfied": True,
                "no_unresolved_blocker_or_material_finding": True,
                "verification_performed": True,
                "material_claims_have_evidence": True,
                "no_unauthorized_scope_expansion": True,
                "no_security_or_permission_bypass": True,
                "artifact_usable": True,
            },
            "evidence": [{"source": "test", "claim": "focused tests passed"}],
        }

    def test_clean_task_is_releasable(self):
        task = CodingTask("run-1", "implement API validation")
        result = run_coding_task(task, self._worker)
        self.assertTrue(result.ready)
        self.assertEqual(result.release.status, "passed")
        verify_provenance(result)
        self.assertEqual(result.provenance.records[-1].event, "release-decision")

    def test_artifact_regression_blocks_release(self):
        task = CodingTask("run-2", "implement API validation")
        with tempfile.TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.txt"
            current_path = Path(tmp) / "current.txt"
            baseline_path.write_text("before", encoding="utf-8")
            current_path.write_text("after", encoding="utf-8")
            result = run_coding_task(
                task,
                self._worker,
                baseline_artifacts=[snapshot_artifact(baseline_path)],
                current_artifacts=[snapshot_artifact(current_path)],
            )
        self.assertFalse(result.ready)
        self.assertEqual(result.regression.status, "failed")
        self.assertEqual(result.release.status, "failed")

    def test_allowed_artifact_change_is_releasable(self):
        task = CodingTask("run-3", "update generated API client", allowed_artifact_changes=("current.txt",))
        with tempfile.TemporaryDirectory() as tmp:
            before_path = Path(tmp) / "baseline.txt"
            current_path = Path(tmp) / "current.txt"
            before_path.write_text("before", encoding="utf-8")
            current_path.write_text("after", encoding="utf-8")
            before = snapshot_artifact(before_path)
            after = snapshot_artifact(current_path)
            result = run_coding_task(task, self._worker, baseline_artifacts=[before], current_artifacts=[after])
        self.assertFalse(result.ready)
        self.assertEqual(result.regression.status, "failed")


if __name__ == "__main__":
    unittest.main()
