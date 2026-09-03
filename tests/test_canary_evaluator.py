import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))

from canary_evaluator import evaluate_canary, evaluate_shadow
from learning_engine import PolicyCandidate
from regression_replay import ReplayCase


class CanaryEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.candidate = PolicyCandidate("policy-test", "dotnet_bug", "targeted_context", "test", ("t1",), .9, "low")
        self.cases = [ReplayCase("a", "dotnet_bug", True), ReplayCase("b", "dotnet_bug", True)]

    def test_shadow_is_non_mutating_and_reports_metrics(self):
        report = evaluate_shadow(self.candidate, self.cases, lambda case, _: (True, True, 10, 100))
        self.assertEqual(report.mode, "shadow")
        self.assertEqual(report.pass_rate, 1.0)
        self.assertEqual(report.verification_rate, 1.0)
        self.assertTrue(report.gate_passed)

    def test_canary_blocks_on_regression(self):
        report = evaluate_canary(self.candidate, self.cases, lambda case, _: (case.case_id == "a", True))
        self.assertFalse(report.gate_passed)
        self.assertEqual(report.failures, ("b",))

    def test_canary_enforces_required_verification(self):
        report = evaluate_canary(self.candidate, self.cases, lambda _case, _candidate: (True, False), min_verification_rate=1.0)
        self.assertFalse(report.gate_passed)

    def test_runner_supports_structured_metrics(self):
        report = evaluate_canary(self.candidate, [self.cases[0]], lambda _case, _candidate: {"success": True, "verified": True, "latency_ms": 42, "token_cost": 123})
        self.assertEqual(report.avg_latency_ms, 42.0)
        self.assertEqual(report.avg_token_cost, 123.0)
        self.assertTrue(report.gate_passed)


if __name__ == "__main__":
    unittest.main()
