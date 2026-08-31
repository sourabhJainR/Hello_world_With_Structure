import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from intent_contract import create_intent_contract, semantic_alignment, verify_intent_contract


class IntentContractTests(unittest.TestCase):
    def test_contract_is_stable_and_has_digest(self):
        a = create_intent_contract('Fix duplicate tenant export rows', protected_behavior=['public API'])
        b = create_intent_contract('Fix duplicate tenant export rows', protected_behavior=['public API'])
        self.assertEqual(a, b)
        self.assertTrue(a['intent_digest'])

    def test_goal_change_is_rejected(self):
        contract = create_intent_contract('Fix duplicate tenant export rows', protected_behavior=['public API'])
        observed = dict(contract)
        observed['goal'] = 'Refactor reporting architecture'
        result = verify_intent_contract(contract, observed)
        self.assertFalse(result['passed'])
        self.assertIn('goal_changed', result['reasons'])
        self.assertIn('intent_digest_mismatch', result['reasons'])

    def test_protected_behavior_and_boundaries_are_immutable(self):
        contract = create_intent_contract('Add tenant filtering', protected_behavior=['existing exports'], boundaries=['export module'])
        observed = dict(contract)
        observed['protected_behavior'] = ['existing exports', 'public API']
        result = verify_intent_contract(contract, observed)
        self.assertFalse(result['passed'])
        self.assertIn('protected_behavior_changed', result['reasons'])

    def test_semantic_alignment_flags_unrelated_direction(self):
        contract = create_intent_contract('Fix tenant export duplication', non_goals=['rewrite reporting'])
        result = semantic_alignment(contract, 'Rewrite reporting architecture and replace the reporting pipeline')
        self.assertTrue(result['non_goal_hits'])
        self.assertFalse(result['aligned'])

    def test_same_task_remains_valid(self):
        contract = create_intent_contract('Add input validation', requirements=['reject invalid input'])
        result = verify_intent_contract(contract, dict(contract))
        self.assertTrue(result['passed'])


if __name__ == '__main__':
    unittest.main()
