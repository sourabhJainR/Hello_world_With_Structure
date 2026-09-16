import unittest

from portable.workflow_evaluation import DecisionObservation, WorkflowEvaluation


class WorkflowEvaluationTests(unittest.TestCase):
    def test_metrics_are_deterministic(self) -> None:
        evaluation = WorkflowEvaluation.from_iterable(
            [
                DecisionObservation("a", 0.9, True, latency_ms=10, token_cost=3),
                DecisionObservation("b", 0.2, False, latency_ms=20, token_cost=5),
            ]
        )
        first = evaluation.summary()
        second = evaluation.summary()
        self.assertEqual(first, second)
        self.assertEqual(evaluation.accuracy(), 1.0)
        self.assertLess(evaluation.brier_score(), 0.05)
        self.assertEqual(evaluation.abstention_rate(), 0.0)

    def test_abstention_is_explicit(self) -> None:
        evaluation = WorkflowEvaluation.from_iterable(
            [DecisionObservation("a", 0.51, True), DecisionObservation("b", 0.5, False, abstained=True)]
        )
        self.assertEqual(evaluation.accuracy(), 1.0)
        self.assertEqual(evaluation.abstention_rate(), 0.5)

    def test_probability_bounds_and_unique_ids(self) -> None:
        with self.assertRaises(ValueError):
            DecisionObservation("bad", 1.1, True)
        with self.assertRaises(ValueError):
            WorkflowEvaluation.from_iterable(
                [DecisionObservation("same", 0.5, True), DecisionObservation("same", 0.4, False)]
            )

    def test_calibration_is_bounded(self) -> None:
        evaluation = WorkflowEvaluation.from_iterable(
            [DecisionObservation("a", 1.0, True), DecisionObservation("b", 0.0, False)]
        )
        self.assertGreaterEqual(evaluation.calibration_error(), 0.0)
        self.assertLessEqual(evaluation.calibration_error(), 1.0)


if __name__ == "__main__":
    unittest.main()
