import unittest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".ai-harness"))

from runtime.capability_catalog import select_capabilities, validate_plan


class CapabilityCatalogTests(unittest.TestCase):
    def test_implementation_gets_builder_and_verifier(self):
        plan = select_capabilities({"mode": "implement", "risk": "low", "uncertainty": "known"})
        self.assertEqual(plan["selected"], ["planner", "builder", "verifier"])
        self.assertEqual(validate_plan(plan)["passed"], True)

    def test_high_risk_gets_independent_reviewers(self):
        plan = select_capabilities({"mode": "implement", "risk": "high", "uncertainty": "known"})
        self.assertIn("security_reviewer", plan["selected"])
        self.assertIn("reviewer", plan["selected"])
        self.assertIn("builder", plan["mutating_capabilities"])

    def test_rca_does_not_select_builder(self):
        plan = select_capabilities({"mode": "rca", "risk": "medium", "uncertainty": "unknown"})
        self.assertIn("explorer", plan["selected"])
        self.assertIn("rca_investigator", plan["selected"])
        self.assertNotIn("builder", plan["selected"])

    def test_invalid_plan_is_rejected(self):
        result = validate_plan({"selected": ["builder", "builder"], "max_parallel_read_only": 1})
        self.assertFalse(result["passed"])
        self.assertIn("duplicate_capability", result["reasons"])


if __name__ == "__main__":
    unittest.main()
