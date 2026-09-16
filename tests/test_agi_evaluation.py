import unittest

from portable.agi_evaluation import CapabilityCase, CapabilityEvaluator


class CapabilityEvaluatorTests(unittest.TestCase):
    def test_reports_pass_fail_and_capability_coverage(self) -> None:
        report = CapabilityEvaluator().evaluate((
            CapabilityCase("novel-1", "novel", "solve", "solve", ("e1",)),
            CapabilityCase("transfer-1", "transfer", "reuse", "adapt", ("e2",)),
            CapabilityCase("memory-1", "memory", "recall", "recall", ("e3",)),
        ))
        self.assertEqual((report.total, report.passed, report.failed), (3, 2, 1))
        self.assertEqual(report.coverage, ("memory", "novel", "transfer"))
        self.assertEqual(len(report.missing_kinds), 7)
        self.assertAlmostEqual(report.pass_rate, 2 / 3)

    def test_missing_evidence_and_duplicate_ids_fail_closed(self) -> None:
        evaluator = CapabilityEvaluator()
        report = evaluator.evaluate((CapabilityCase("x", "reasoning", "a", "a"),))
        self.assertFalse(report.results[0].passed)
        self.assertEqual(report.results[0].reason, "missing evidence")
        with self.assertRaises(ValueError):
            evaluator.evaluate((
                CapabilityCase("x", "reasoning", "a", "a", ("e1",)),
                CapabilityCase("x", "reasoning", "a", "a", ("e2",)),
            ))
        with self.assertRaises(ValueError):
            CapabilityCase("x", "unknown", "a", "a", ("e1",))


if __name__ == "__main__":
    unittest.main()
