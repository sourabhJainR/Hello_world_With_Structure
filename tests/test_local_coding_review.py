import unittest
from portable.local_coding_review import deterministic_quality, parse_findings

class LocalCodingReviewTests(unittest.TestCase):
    def test_parse_structured_finding(self):
        text = """FINDINGS
- severity: high
  location: portable/foo.py:10
  evidence: existing retry path
  impact: regression risk
  remedy: add regression test
  confidence: 0.8"""
        findings = parse_findings(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "high")

    def test_quality_requires_repository_evidence(self):
        text = """- severity: medium
  location: portable/foo.py:10
  evidence: existing helper
  impact: compatibility break
  remedy: reuse helper
  confidence: 0.7"""
        quality = deterministic_quality(text, "portable/foo.py:10 existing helper")
        self.assertEqual(quality["grounded"], 1)
        self.assertEqual(quality["actionable"], 1)
        self.assertEqual(quality["regression_aware"], 1)

    def test_unstructured_output_is_not_counted(self):
        self.assertEqual(deterministic_quality("Looks good", "portable/foo.py"), {
            "findings": 0, "grounded": 0, "actionable": 0, "regression_aware": 0})

if __name__ == "__main__":
    unittest.main()
