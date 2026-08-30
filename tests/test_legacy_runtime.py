import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from legacy import compare_shapes, shape_fingerprint, flow_step, variant, impact_closure


class LegacyRuntimeTests(unittest.TestCase):
    def test_shape_fingerprint_excludes_values(self):
        a = shape_fingerprint({'tenant': 'A', 'amount': 10})
        b = shape_fingerprint({'tenant': 'B', 'amount': 99})
        self.assertEqual(a['id'], b['id'])
        self.assertNotIn('A', repr(a))
        self.assertNotIn('B', repr(b))

    def test_shape_difference_is_explicit(self):
        result = compare_shapes({'id': 1, 'items': []}, {'id': 1, 'items': {}})
        self.assertFalse(result['compatible'])

    def test_flow_and_variant_are_evidence_ready(self):
        step = flow_step('ExportService', 'filter', ['request'], ['rows'], ['tenant_scope'], ['ev-1'])
        v = variant('ExportService', 'rows_empty', step['id'], ['ev-2'])
        self.assertEqual(step['evidence_ids'], ['ev-1'])
        self.assertEqual(v['evidence_ids'], ['ev-2'])

    def test_impact_closure_is_bounded_and_cycle_safe(self):
        edges = [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'c'},
            {'source': 'c', 'target': 'a'},
        ]
        result = impact_closure(edges, ['a'], max_nodes=3)
        self.assertEqual(result['nodes'], ['a', 'b', 'c'])
        self.assertFalse(result['truncated'])


if __name__ == '__main__':
    unittest.main()
