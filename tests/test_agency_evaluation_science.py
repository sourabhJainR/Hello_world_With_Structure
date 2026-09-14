import unittest

from portable.agency_evaluation_science import paired_delta, select_candidate, summarize


class AgencyEvaluationScienceTests(unittest.TestCase):
    def test_summary_reports_confidence_interval(self):
        summary = summarize("quality", [0.8, 0.9, 1.0])
        self.assertEqual(summary.count, 3)
        self.assertLessEqual(summary.confidence_low, summary.mean)
        self.assertLessEqual(summary.mean, summary.confidence_high)

    def test_paired_delta_and_candidate_selection(self):
        delta = paired_delta([0.7, 0.8], [0.8, 0.9])
        self.assertAlmostEqual(delta.mean, 0.1)
        winner, summaries = select_candidate({"a": [0.8, 0.81], "b": [0.9, 0.91]}, minimum_mean=0.85)
        self.assertEqual(winner, "b")
        self.assertEqual(len(summaries), 2)

    def test_paired_delta_preserves_negative_confidence_interval(self):
        delta = paired_delta([0.9, 1.0, 0.8], [0.7, 0.8, 0.6])
        self.assertLess(delta.confidence_high, 0.0)


if __name__ == "__main__":
    unittest.main()
