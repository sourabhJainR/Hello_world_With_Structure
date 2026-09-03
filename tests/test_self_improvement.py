import unittest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))

from self_improvement import (  # noqa: E402
    ImprovementProposal,
    Outcome,
    evaluate_proposal,
    learning_record,
    propose_improvements,
    summarize_outcomes,
)


class SelfImprovementTests(unittest.TestCase):
    def test_summary_tracks_outcomes(self):
        summary = summarize_outcomes([
            Outcome("a", "implement", True, True, True),
            Outcome("b", "debug", False, False, False, regressions=1, failure_class="test_failure"),
        ])
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["accepted_rate"], 0.5)
        self.assertEqual(summary["regression_rate"], 0.5)

    def test_repeated_failure_creates_guardrail_proposal(self):
        outcomes = [
            Outcome("a", "implement", False, False, False, failure_class="missing_regression_test"),
            Outcome("b", "implement", False, False, False, failure_class="missing_regression_test"),
        ]
        proposals = propose_improvements(outcomes)
        self.assertTrue(any(p.category == "workflow_guardrail" for p in proposals))

    def test_thrashing_creates_strategy_change(self):
        outcomes = [
            Outcome("a", "debug", True, True, True, retries=4),
            Outcome("b", "debug", True, True, True, retries=5),
        ]
        proposals = propose_improvements(outcomes)
        self.assertTrue(any(p.category == "context_or_routing" for p in proposals))

    def test_promotion_requires_both_gates(self):
        proposal = ImprovementProposal("x", "workflow_guardrail", "change", "reason", ("a",), 0.8)
        rejected = evaluate_proposal(proposal, regression_gate=lambda _: True, safety_gate=lambda _: False)
        accepted = evaluate_proposal(proposal, regression_gate=lambda _: True, safety_gate=lambda _: True)
        self.assertFalse(rejected.executable)
        self.assertTrue(accepted.executable)

    def test_learning_record_is_audit_friendly(self):
        proposal = ImprovementProposal("x", "context_efficiency", "change", "reason", ("a",), 0.8)
        record = learning_record(proposal=proposal, promoted=True, evaluated_at=123)
        self.assertEqual(record["type"], "improvement_evaluation")
        self.assertEqual(record["evaluated_at"], 123)
        self.assertTrue(record["promoted"])


if __name__ == "__main__":
    unittest.main()
