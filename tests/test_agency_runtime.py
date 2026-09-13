import unittest

from portable.agency_quality import ReviewFinding
from portable.agency_runtime import EvidenceItem, TaskProfile, evidence_id, execute, plan_task


REGISTRY = {
    "agents": [
        {"name": "backend-engineer", "division": "engineering", "description": "api backend code architecture"},
        {"name": "test-engineer", "division": "testing", "description": "quality validation regression tests"},
        {"name": "security-engineer", "division": "security", "description": "auth vulnerability security review"},
    ]
}


class AgencyRuntimeTests(unittest.TestCase):
    def test_plan_is_deterministic_and_has_primary(self):
        task = TaskProfile("T1", "fix backend api bug and test", artifact_type="code")
        first = plan_task(task, REGISTRY)
        second = plan_task(task, REGISTRY)
        self.assertEqual(first, second)
        self.assertEqual(first[0].role, "primary")
        self.assertTrue(any(x.role == "reviewer" for x in first))

    def test_evidence_ids_are_stable(self):
        item = EvidenceItem("test", "tests passed", "run-42")
        self.assertEqual(evidence_id(item), evidence_id(item))

    def test_execute_produces_traceable_receipt(self):
        task = TaskProfile("T2", "implement api change", artifact_type="code")
        rubric = {"release_threshold": 90, "dimensions": {"correctness": 30, "completeness": 30, "evidence": 20, "verification": 20}}

        def worker(_task, _assignments):
            return {
                "deliverables": ["portable/feature.py"],
                "evidence": [EvidenceItem("unit-tests", "all targeted tests passed", "test-run")],
                "verification": ["unit tests passed"],
                "dimensions": {"correctness": 30, "completeness": 30, "evidence": 20, "verification": 20},
                "hard_gates": {"acceptance": True, "verification": True},
            }

        result = execute(task, worker, registry=REGISTRY, rubric=rubric)
        self.assertTrue(result.receipt.passed)
        self.assertEqual(len(result.evidence), 1)
        self.assertTrue(result.ledger[0].event_id)

    def test_material_finding_blocks_release(self):
        task = TaskProfile("T3", "fix security auth bug", artifact_type="code")

        def worker(_task, _assignments):
            return {
                "deliverables": ["auth.py"],
                "evidence": [EvidenceItem("review", "permission boundary checked")],
                "verification": ["review completed"],
                "dimensions": {"correctness": 30, "completeness": 30, "evidence": 20, "verification": 20},
                "hard_gates": {"acceptance": True, "verification": True},
                "findings": [ReviewFinding("material", "missing negative authorization test", "review-1")],
            }
        rubric = {"release_threshold": 90, "dimensions": {"correctness": 30, "completeness": 30, "evidence": 20, "verification": 20}}
        result = execute(task, worker, registry=REGISTRY, rubric=rubric)
        self.assertFalse(result.receipt.passed)


if __name__ == "__main__":
    unittest.main()
