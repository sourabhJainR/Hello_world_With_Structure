import unittest

from portable.agency_quality import ReviewFinding, evaluate, score_dimensions


RUBRIC = {
    "release_threshold": 90,
    "dimensions": {
        "correctness": 25,
        "completeness": 15,
        "evidence": 15,
        "verification": 15,
        "scope_discipline": 10,
        "security_and_safety": 10,
        "clarity": 5,
        "maintainability": 5,
    },
}


class AgencyQualityTests(unittest.TestCase):
    def test_score_dimensions_caps_values(self):
        self.assertEqual(score_dimensions({"correctness": 25, "completeness": 15}, RUBRIC), 40)

    def test_score_dimensions_rejects_unknown_dimension(self):
        with self.assertRaises(ValueError):
            score_dimensions({"not_in_rubric": 1}, RUBRIC)

    def test_receipt_requires_score_gates_and_no_material_findings(self):
        receipt = evaluate(
            {name: cap for name, cap in RUBRIC["dimensions"].items()},
            {"acceptance": True, "verification": True},
            rubric=RUBRIC,
        )
        self.assertTrue(receipt.passed)

        blocked = evaluate(
            {name: cap for name, cap in RUBRIC["dimensions"].items()},
            {"acceptance": True, "verification": True},
            [ReviewFinding("material", "API behavior is not backward compatible")],
            rubric=RUBRIC,
        )
        self.assertFalse(blocked.passed)

    def test_finding_severity_is_validated(self):
        with self.assertRaises(ValueError):
            ReviewFinding("critical", "bad")

    def test_default_rubric_supports_standard_dimensions(self):
        receipt = evaluate({name: cap for name, cap in RUBRIC["dimensions"].items()}, {"verification": True})
        self.assertEqual(receipt.score, 100)
        self.assertEqual(receipt.threshold, 90)


if __name__ == "__main__":
    unittest.main()
