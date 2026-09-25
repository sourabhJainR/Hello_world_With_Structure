import unittest
from portable.coding_review_evaluation import (
    CodingReviewEvaluator, CodingReviewObservation,
)


class CodingReviewEvaluationTests(unittest.TestCase):
    def test_empty_calibration_is_not_usable(self):
        result = CodingReviewEvaluator().evaluate([])
        self.assertFalse(result.usable)
        self.assertEqual(result.samples, 0)

    def test_hallucinated_review_is_never_grounded_or_verified(self):
        with self.assertRaises(ValueError):
            CodingReviewObservation("r1", 0.9, False, True, False, False, True)

    def test_calibration_requires_verified_history(self):
        evaluator = CodingReviewEvaluator(min_samples=2)
        rows = [
            CodingReviewObservation("r1", 0.9, True, True, True, True),
            CodingReviewObservation("r2", 0.8, True, True, True, True),
        ]
        result = evaluator.evaluate(rows)
        self.assertTrue(result.usable)
        self.assertLess(result.calibration_error, 0.2)

    def test_bad_local_review_is_gated(self):
        evaluator = CodingReviewEvaluator(min_samples=2)
        rows = [
            CodingReviewObservation("r1", 0.9, False, False, False, False, True),
            CodingReviewObservation("r2", 0.8, False, False, False, False, True),
        ]
        result = evaluator.evaluate(rows)
        self.assertFalse(result.usable)
        self.assertFalse(evaluator.admission(result)["usable"])

    def test_metrics_are_bounded_and_deterministic(self):
        evaluator = CodingReviewEvaluator(min_samples=1)
        row = CodingReviewObservation("r1", 0.5, True, True, False, True)
        a = evaluator.evaluate([row]).as_dict()
        b = evaluator.evaluate([row]).as_dict()
        self.assertEqual(a, b)
        for key in ("validity_rate", "grounding_rate", "actionable_rate",
                    "regression_awareness_rate", "hallucination_rate", "calibration_error"):
            self.assertGreaterEqual(a[key], 0.0)
            self.assertLessEqual(a[key], 1.0)


if __name__ == "__main__":
    unittest.main()
