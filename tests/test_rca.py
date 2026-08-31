import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from rca import rca_contract, finding, hypothesis, report


class RCATests(unittest.TestCase):
    def test_rca_contract_is_analysis_only(self):
        contract = rca_contract('Find the root cause of duplicate exports')
        self.assertEqual(contract['mode'], 'analysis-only')
        self.assertFalse(contract['patch_allowed'])

    def test_findings_require_evidence_shape(self):
        item = finding('fact', 'Tenant filter is bypassed for empty items', ['ev-1'], 'high')
        self.assertEqual(item['evidence_ids'], ['ev-1'])
        self.assertEqual(item['kind'], 'fact')

    def test_hypothesis_keeps_support_and_contradiction_separate(self):
        item = hypothesis('Fallback path is selected for empty payload', ['ev-1'], ['ev-2'], 'medium')
        self.assertEqual(item['evidence_for'], ['ev-1'])
        self.assertEqual(item['evidence_against'], ['ev-2'])

    def test_report_never_becomes_patch_plan(self):
        result = report('Investigate duplicate export', [], [], [], [], [], ['unknown data-shape source'], ['production trace'], {'status': 'unproven'}, ['capture representative payload'])
        self.assertFalse(result['patch_allowed'])
        self.assertEqual(result['root_cause']['status'], 'unproven')
        self.assertEqual(result['follow_up'], ['capture representative payload'])


if __name__ == '__main__':
    unittest.main()
