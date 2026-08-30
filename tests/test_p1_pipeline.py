import sys
import unittest
from pathlib import Path

RUNTIME = Path(__file__).parents[1] / '.ai-harness' / 'runtime'
sys.path.insert(0, str(RUNTIME))

from p1_pipeline import apply_route, build_task_state, finalize_proof, negotiate_extensions, plan_controls, record_verification, seed_regression


class P1PipelineTests(unittest.TestCase):
    def test_pipeline_keeps_evidence_chain(self):
        state = build_task_state('T1', 'Fix export timeout', facts={'tests': {'status': 'observed', 'value': 'native'}})
        apply_route(state, {'mode': 'debug', 'risk': 'medium', 'uncertainty': 'moderate'})
        record_verification(state, 'unit', 'passed', 'test command')
        proof = finalize_proof(state)
        evidence_ids = {item['id'] for item in state['evidence']}
        self.assertTrue(state['decisions'][0]['evidence_ids'][0] in evidence_ids)
        self.assertTrue(state['verification'][0]['evidence_ids'][0] in evidence_ids)
        self.assertEqual(proof['proof_id'], finalize_proof(state)['proof_id'])

    def test_risk_controls_are_derived_not_model_selected(self):
        state = build_task_state('T2', 'Change auth')
        plan_controls(state, {'security_risk': 3})
        self.assertEqual(state['metadata']['risk']['level'], 'critical')
        self.assertIn('isolated_execution', state['metadata']['risk']['controls'])
        self.assertIn('explicit_approval', state['metadata']['risk']['controls'])

    def test_optional_extensions_never_block_core(self):
        state = build_task_state('T3', 'Explain architecture')
        negotiate_extensions(state, ['graph.search'], [])
        self.assertTrue(state['metadata']['extensions']['degraded'])
        self.assertFalse(state['metadata']['extensions']['compatible'])
        self.assertTrue(state['evidence'])

    def test_profile_invalidation_is_recorded(self):
        state = build_task_state('T4', 'Update deployment', changed_paths=['deploy/Dockerfile'])
        self.assertEqual(state['metadata']['invalidated_profile_fields'], ['deployment'])

    def test_regression_seed_is_stable(self):
        a = seed_regression('duplicate export', 'blocked', ['no api change'])
        b = seed_regression('duplicate export', 'blocked', ['no api change'])
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
