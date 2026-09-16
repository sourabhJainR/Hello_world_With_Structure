import unittest

from portable.deep_evaluation import BenchmarkCase, DeepEvaluator


class DeepEvaluationTests(unittest.TestCase):
    def test_reports_per_kind_and_calibration_metrics(self) -> None:
        cases = [
            BenchmarkCase("r1", "reasoning", "ok", "ok", ("e1",), 0.9, "easy", "finance"),
            BenchmarkCase("r2", "reasoning", "ok", "bad", ("e2",), 0.2, "hard", "finance"),
            BenchmarkCase("a1", "adversarial", "ok", "ok", ("e3",), 0.8, "hard", "security"),
        ]
        report = DeepEvaluator().run(cases, required_kinds=("reasoning", "adversarial"), min_cases_per_kind=1)
        self.assertEqual(report.total, 3)
        self.assertAlmostEqual(report.pass_rate, 2 / 3)
        self.assertEqual(report.per_kind["reasoning"], 0.5)
        self.assertEqual(report.adversarial_pass_rate, 1.0)
        self.assertGreater(report.calibration_mae, 0)
        self.assertEqual(report.domains, ("finance", "security"))

    def test_missing_required_kind_and_duplicate_ids_fail_closed(self) -> None:
        evaluator = DeepEvaluator()
        with self.assertRaises(ValueError):
            evaluator.run([BenchmarkCase("r1", "reasoning", "ok", "ok", ("e",), 1.0, "easy", "x")], required_kinds=("reasoning", "causal"))
        with self.assertRaises(ValueError):
            evaluator.run([BenchmarkCase("r1", "reasoning", "ok", "ok", ("e",), 1.0, "easy", "x")], required_kinds=("reasoning",), min_cases_per_kind=2)
        with self.assertRaises(ValueError):
            evaluator.run([
                BenchmarkCase("r1", "reasoning", "ok", "ok", ("e",), 1.0, "easy", "x"),
                BenchmarkCase("r1", "reasoning", "ok", "ok", ("e2",), 1.0, "easy", "x"),
            ])

    def test_missing_evidence_is_measured_as_a_failed_case(self) -> None:
        report = DeepEvaluator().run([BenchmarkCase("r1", "reasoning", "ok", "ok", (), 1.0, "easy", "x")])
        self.assertEqual(report.pass_rate, 0.0)
        self.assertEqual(report.evidence_rate, 0.0)

    def test_confidence_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            DeepEvaluator().run([BenchmarkCase("r1", "reasoning", "ok", "ok", ("e",), 1.1, "easy", "x")])


if __name__ == "__main__":
    unittest.main()
