import sys
import unittest
from pathlib import Path

RUNTIME = Path(__file__).parents[1] / '.ai-harness' / 'runtime'
sys.path.insert(0, str(RUNTIME))
from legacy import compare_shapes, shape_fingerprint, flow_step, variant, impact_closure
from execution_controls import checkpoint, context_integrity, scope_check, task_chunks


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
        edges = [{'source': 'a', 'target': 'b'}, {'source': 'b', 'target': 'c'}, {'source': 'c', 'target': 'a'}]
        result = impact_closure(edges, ['a'], max_nodes=3)
        self.assertEqual(result['nodes'], ['a', 'b', 'c'])
        self.assertFalse(result['truncated'])

    def test_scope_fence_blocks_outside_changes(self):
        self.assertTrue(scope_check(['src/export/service.py'], ['src/export'])['passed'])
        result = scope_check(['src/export/service.py', 'docs/unrelated.md'], ['src/export'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['outside_scope'], ['docs/unrelated.md'])

    def test_task_chunking_scales_only_when_needed(self):
        self.assertEqual(len(task_chunks('rename helper')), 1)
        chunks = task_chunks('legacy API security migration across data shape paths', complexity=8)
        self.assertGreaterEqual(len(chunks), 5)
        self.assertTrue(any(item['goal'] == 'data-shapes' for item in chunks))

    def test_context_integrity_detects_rot(self):
        result = context_integrity('fix export', {'goal': 'fix export'}, 'unrelated answer', ['preserve API', 'add regression'])
        self.assertTrue(result['context_rot'])
        self.assertTrue(result['guardrail_loss'])

    def test_checkpoint_is_deterministic(self):
        state = {'task': 'T', 'status': 'implementing'}
        a = checkpoint('run-1', 'execute', 2, 4, state, ['src/a.py'], 'output', ['task boundary'], ['src'])
        b = checkpoint('run-1', 'execute', 2, 4, state, ['src/a.py'], 'output', ['task boundary'], ['src'])
        self.assertEqual(a, b)
        self.assertEqual(a['next'], 'continue')


if __name__ == '__main__':
    unittest.main()
