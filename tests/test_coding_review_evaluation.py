import unittest
from portable.coding_review_evaluation import CodingReviewEvaluator, CodingReviewObservation

class CodingReviewEvaluationTests(unittest.TestCase):
    def test_unverified_history_cannot_calibrate(self):
        result = CodingReviewEvaluator(min_samples=1).evaluate([
            CodingReviewObservation("r1", 0.9, True, True, True, True)
        ])
        self.assertFalse(result.usable)
        self.assertEqual(result.samples, 0)

    def test_verified_history_can_calibrate(self):
        evaluator = CodingReviewEvaluator(min_samples=2)
        rows = [
            CodingReviewObservation("r1", 0.9, True, True, True, True, verified=True),
            CodingReviewObservation("r2", 0.8, True, True, True, True, verified=True),
        ]
        result = evaluator.evaluate(rows)
        self.assertTrue(result.usable)
        self.assertLess(result.calibration_error, 0.2)

    def test_hallucinated_review_is_never_verified(self):
        with self.assertRaises(ValueError):
            CodingReviewObservation("r1", 0.9, False, True, False, False, True, True)

    def test_bad_verified_review_is_gated(self):
        evaluator = CodingReviewEvaluator(min_samples=2)
        rows = [
            CodingReviewObservation("r1", 0.9, False, False, False, False, verified=True),
            CodingReviewObservation("r2", 0.8, False, False, False, False, verified=True),
        ]
        result = evaluator.evaluate(rows)
        self.assertFalse(result.usable)
        self.assertFalse(evaluator.admission(result)["usable"])

if __name__ == "__main__":
    unittest.main()
