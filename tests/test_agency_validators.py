import unittest

from portable.agency_validators import validate_result


class AgencyValidatorTests(unittest.TestCase):
    def test_code_requires_explicit_verification(self):
        result = validate_result("code", ["x.py"], [{"source": "review", "claim": "scope checked"}], ["review completed"])
        self.assertFalse(result.hard_gates["deliverable_present"] is False)
        self.assertTrue(any(f.severity == "material" for f in result.findings))

    def test_security_permission_bypass_is_blocker(self):
        result = validate_result(
            "security", ["policy"], [{"source": "scan", "claim": "checked"}], ["negative-path test passed"],
            {"permission_bypass": True},
        )
        self.assertTrue(any(f.severity == "blocker" for f in result.findings))

    def test_finance_requires_calculation_basis(self):
        result = validate_result("finance", ["memo"], [{"source": "filing", "claim": "revenue"}], ["reviewed"])
        self.assertTrue(any("calculation basis" in f.message for f in result.findings))

    def test_research_requires_sources(self):
        result = validate_result("research", ["report"], [{"source": "model", "claim": "finding"}], ["reviewed"])
        self.assertTrue(any("source-backed" in f.message for f in result.findings))


if __name__ == "__main__":
    unittest.main()
