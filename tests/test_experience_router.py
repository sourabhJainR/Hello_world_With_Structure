import json
import tempfile
import unittest
from pathlib import Path

from portable.experience_router import ExperienceRouter
from portable.learning_steward import LearningSteward


class ExperienceRouterTests(unittest.TestCase):
    def test_capability_selection_uses_historical_success_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steward = LearningSteward(root, run_id="seed", task="task")
            for _ in range(5):
                steward.record_experience(
                    key="builder:task:capability:file",
                    outcome="worked",
                    evidence_quality=0.95,
                    cost_score=0.2,
                    duration_seconds=2,
                    decision="file",
                )
            choice = ExperienceRouter(root).choose_capability(
                ("file", "delegate_task"), key_prefix="builder:task"
            )
            self.assertEqual(choice.selected, "file")

    def test_verification_and_retry_escalate_from_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            router = ExperienceRouter(root)
            verification = router.verification_depth(
                key="verifier:task", risk=0.95, evidence_quality=0.2
            )
            retry = router.retry_or_escalate(
                key="verifier:task", risk=0.2, failure_probability=0.8
            )
            self.assertEqual(verification.level, "human")
            self.assertEqual(retry.selected, "retry")

    def test_counterfactual_selection_accounts_for_cost_and_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            choice = ExperienceRouter(Path(tmp)).counterfactual([
                {"name": "cheap", "success_probability": 0.8, "evidence_value": 0.8, "cost": 0.1, "risk": 0.1},
                {"name": "expensive", "success_probability": 0.95, "evidence_value": 0.95, "cost": 0.9, "risk": 0.2},
            ])
            self.assertEqual(choice.selected, "cheap")


if __name__ == "__main__":
    unittest.main()
