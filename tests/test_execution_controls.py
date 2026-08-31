import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from execution_controls import checkpoint, context_integrity, guard_check, scope_check, task_chunks

class ExecutionControlTests(unittest.TestCase):
    def test_scope_fence(self):
        self.assertTrue(scope_check(['src/a.py'], ['src'])['passed'])
        result = scope_check(['src/a.py', 'docs/x.md'], ['src'], ['src/private'])
        self.assertFalse(result['passed']); self.assertEqual(result['outside_scope'], ['docs/x.md'])

    def test_task_chunking_scales(self):
        self.assertEqual(len(task_chunks('rename helper')), 1)
        self.assertGreaterEqual(len(task_chunks('legacy API security migration across data shape paths', complexity=8)), 5)

    def test_context_rot_and_guardrail_loss(self):
        result = context_integrity('fix export', {'goal': 'fix export'}, 'unrelated answer', ['preserve API', 'add regression'])
        self.assertTrue(result['context_rot']); self.assertTrue(result['guardrail_loss'])
        unsafe = guard_check('fix export', {'goal': 'fix export'}, 'verified with no regression', ['preserve API'], ['src/a.py'], ['src'], evidence_markers=['test'])
        self.assertFalse(unsafe['passed'])
        safe = guard_check('fix export', {'goal': 'fix export'}, 'I preserved API and attached test evidence.', ['preserve API'], ['src/a.py'], ['src'], evidence_markers=['test'])
        self.assertTrue(safe['passed'])

    def test_checkpoint_is_deterministic(self):
        state={'task':'T','status':'implementing'}
        a=checkpoint('run-1','execute',2,4,state,['src/a.py'],'output',['preserve API'],['src'])
        b=checkpoint('run-1','execute',2,4,state,['src/a.py'],'output',['preserve API'],['src'])
        self.assertEqual(a,b)

if __name__ == '__main__': unittest.main()
