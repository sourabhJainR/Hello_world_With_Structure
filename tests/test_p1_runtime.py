import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from p1 import profile, affected_profile_fields, regression_case, regression_result, graph_node, graph_edge, extension_manifest, negotiate

class P1RuntimeTests(unittest.TestCase):
    def test_profile_preserves_provenance(self):
        p = profile('demo', {'tests': {'status': 'observed', 'value': 'pytest', 'evidence_ids': ['e2', 'e1']}})
        self.assertEqual(p['profile_version'], '1.0')
        self.assertEqual(p['facts']['tests']['evidence_ids'], ['e1', 'e2'])

    def test_profile_invalidation_is_targeted(self):
        fields = affected_profile_fields(['src/export/handler.py', 'deploy/Dockerfile'])
        self.assertIn('architecture', fields)
        self.assertIn('deployment', fields)
        self.assertNotIn('security', fields)

    def test_regression_case_is_deterministic(self):
        a = regression_case('duplicate export', 'blocked', ['no api change'])
        b = regression_case('duplicate export', 'blocked', ['no api change'])
        self.assertEqual(a, b)
        self.assertTrue(regression_result(a, 'blocked')['passed'])
        self.assertFalse(regression_result(a, 'allowed')['passed'])

    def test_graph_edges_can_carry_evidence(self):
        n = graph_node('service', 'export')
        e = graph_edge(n['id'], 'calls', 'svc-filter', ['ev-1'])
        self.assertEqual(e['evidence_ids'], ['ev-1'])

    def test_optional_extensions_degrade_safely(self):
        result = negotiate(['graph.search', 'memory.read'], [extension_manifest('memory', ['memory.read'])])
        self.assertFalse(result['compatible'])
        self.assertTrue(result['degraded'])
        self.assertEqual(result['missing'], ['graph.search'])

if __name__ == '__main__':
    unittest.main()
