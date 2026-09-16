import unittest

from portable.empirical_improvement import EmpiricalImprovement, ImprovementObservation


class EmpiricalImprovementTests(unittest.TestCase):
    def test_accepts_verified_quality_gain_without_more_iterations(self):
        baseline = [
            ImprovementObservation("c1", "baseline", 0.80, 3, 0.70, ("e1",)),
            ImprovementObservation("c2", "baseline", 0.80, 2, 0.70, ("e2",)),
        ]
        candidate = [
            ImprovementObservation("c1", "candidate", 0.95, 2, 0.90, ("e3",)),
            ImprovementObservation("c2", "candidate", 0.95, 2, 0.90, ("e4",)),
        ]
        report = EmpiricalImprovement.evaluate(baseline, candidate)
        self.assertTrue(report.accepted)
        self.assertGreater(report.score_delta, 0.01)
        self.assertLessEqual(report.iteration_delta, 0)

    def test_rejects_candidate_that_increases_iterations(self):
        baseline = [ImprovementObservation("c1", "baseline", 0.90, 1, 0.90, ("e1",))]
        candidate = [ImprovementObservation("c1", "candidate", 0.92, 2, 0.90, ("e2",))]
        report = EmpiricalImprovement.evaluate(baseline, candidate)
        self.assertFalse(report.accepted)
        self.assertIn("iterations", report.reason)

    def test_rejects_missing_evidence(self):
        baseline = [ImprovementObservation("c1", "baseline", 0.80, 1, 0.80, ("e1",))]
        candidate = [ImprovementObservation("c1", "candidate", 0.95, 1, 0.95, ())]
        report = EmpiricalImprovement.evaluate(baseline, candidate)
        self.assertFalse(report.accepted)
        self.assertIn("evidence", report.reason)

    def test_rejects_quality_regression_even_when_iterations_drop(self):
        baseline = [ImprovementObservation("c1", "baseline", 0.95, 3, 0.95, ("e1",))]
        candidate = [ImprovementObservation("c1", "candidate", 0.70, 1, 0.80, ("e2",))]
        report = EmpiricalImprovement.evaluate(baseline, candidate)
        self.assertFalse(report.accepted)
        self.assertLess(report.score_delta, 0)

    def test_digest_is_stable_for_identical_observations(self):
        baseline = [ImprovementObservation("c1", "baseline", 0.80, 2, 0.80, ("e1",))]
        candidate = [ImprovementObservation("c1", "candidate", 0.90, 2, 0.90, ("e2",))]
        first = EmpiricalImprovement.evaluate(baseline, candidate)
        second = EmpiricalImprovement.evaluate(baseline, candidate)
        self.assertEqual(first.digest, second.digest)


if __name__ == "__main__":
    unittest.main()
