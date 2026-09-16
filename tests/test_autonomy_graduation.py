import unittest

from portable.agi_evaluation import CapabilityCase, CapabilityEvaluator
from portable.autonomy_graduation import AutonomyEvidence, AutonomyGraduator, GraduationPolicy
from portable.self_model import CapabilityProfile


class AutonomyGraduationTests(unittest.TestCase):
    def _report(self, passed: bool = True):
        observed = "ok" if passed else "bad"
        return CapabilityEvaluator().evaluate([
            CapabilityCase(f"c{i}", kind, "ok", observed, (f"e{i}",))
            for i, kind in enumerate(("novel", "transfer", "memory", "reasoning", "causal"))
        ])

    def test_gate_requires_all_independent_controls(self) -> None:
        policy = GraduationPolicy(min_coverage=5, min_pass_rate=0.9, min_observations=10, min_confidence=0.9)
        evidence = AutonomyEvidence(self._report(), CapabilityProfile("coding", 9, 1, 0.9, 10), True, True, False)
        receipt = AutonomyGraduator().evaluate("supervised", evidence, policy)
        self.assertFalse(receipt.eligible)
        self.assertIn("human approval is required", receipt.reasons)

    def test_ready_evidence_can_qualify_without_granting_permissions(self) -> None:
        policy = GraduationPolicy(min_coverage=5, min_pass_rate=0.9, min_observations=10, min_confidence=0.9)
        evidence = AutonomyEvidence(self._report(), CapabilityProfile("coding", 10, 0, 1.0, 10), True, True, True)
        receipt = AutonomyGraduator().evaluate("supervised", evidence, policy)
        self.assertTrue(receipt.eligible)
        self.assertFalse(receipt.grants_permission)

    def test_regression_and_failed_evaluation_block(self) -> None:
        policy = GraduationPolicy(min_coverage=5, min_pass_rate=0.9, min_observations=10, min_confidence=0.9)
        evidence = AutonomyEvidence(self._report(False), CapabilityProfile("coding", 10, 0, 1.0, 10), False, True, True)
        receipt = AutonomyGraduator().evaluate("supervised", evidence, policy)
        self.assertFalse(receipt.eligible)
        self.assertIn("evaluation pass-rate below gate", receipt.reasons)
        self.assertIn("regression gate failed", receipt.reasons)

    def test_unknown_level_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            AutonomyGraduator().evaluate("unknown", AutonomyEvidence(self._report(), CapabilityProfile("x", 10, 0, 1, 10), True, True, True), GraduationPolicy())


if __name__ == "__main__":
    unittest.main()
