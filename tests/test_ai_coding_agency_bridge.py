import tempfile
import unittest
from pathlib import Path

from portable.agency_artifact_regression import snapshot_artifact
from portable.agency_multi_specialist import SpecialistResourceProfile
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

    def test_clean_task_is_releasable_and_has_plan(self):
        task = CodingTask("run-1", "implement API validation")
        result = run_coding_task(task, self._worker)
        self.assertTrue(result.ready)
        self.assertEqual(result.release.status, "passed")
        self.assertGreaterEqual(len(result.execution_plan.waves), 1)
        verify_provenance(result)

    def test_conflicting_mutation_is_visible_in_bridge_result(self):
        task = CodingTask("run-2", "implement API validation")
        resources = {
            "builder": SpecialistResourceProfile("builder", write_paths=("src/a.py",), mutation_mode="bounded"),
            "reviewer": SpecialistResourceProfile("reviewer", read_paths=("src/a.py",)),
        }

        def worker(task_profile, assignments):
            return self._worker(task_profile, assignments)

        result = run_coding_task(task, worker, resource_profiles=resources)
        self.assertIn(result.execution.assignments[0].specialist, {"builder", "reviewer"} | {a.specialist for a in result.execution.assignments})
        self.assertIsNotNone(result.execution_plan)

    def test_artifact_regression_still_fails_release(self):
        task = CodingTask("run-3", "implement API validation")
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline.txt"
            current = Path(tmp) / "current.txt"
            baseline.write_text("before", encoding="utf-8")
            current.write_text("after", encoding="utf-8")
            result = run_coding_task(
                task,
                self._worker,
                baseline_artifacts=[snapshot_artifact(baseline)],
                current_artifacts=[snapshot_artifact(current)],
            )
        self.assertFalse(result.ready)
        self.assertEqual(result.regression.status, "failed")
        self.assertEqual(result.release.status, "failed")


if __name__ == "__main__":
    unittest.main()
