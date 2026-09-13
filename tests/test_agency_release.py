import unittest

from portable.agency_quality import ReviewFinding
from portable.agency_release import decide_release


class AgencyReleaseTests(unittest.TestCase):
    def test_empty_gates_are_blocked(self):
        decision = decide_release(100, 90, {})
        self.assertEqual(decision.status, "blocked")

    def test_unresolved_risk_fails_release(self):
        decision = decide_release(100, 90, {"acceptance": True}, unresolved_risks=["deployment not verified"])
        self.assertEqual(decision.status, "failed")

    def test_material_finding_fails_release(self):
        finding = ReviewFinding("material", "missing regression test")
        decision = decide_release(100, 90, {"acceptance": True}, [finding])
        self.assertEqual(decision.status, "failed")

    def test_regression_fails_release(self):
        decision = decide_release(100, 90, {"acceptance": True}, regression_status="failed")
        self.assertEqual(decision.status, "failed")

    def test_invalid_regression_status_rejected(self):
        with self.assertRaises(ValueError):
            decide_release(100, 90, {"acceptance": True}, regression_status="unknown")

    def test_clean_result_passes(self):
        decision = decide_release(95, 90, {"acceptance": True, "verification": True})
        self.assertTrue(decision.releasable)


if __name__ == "__main__":
    unittest.main()
