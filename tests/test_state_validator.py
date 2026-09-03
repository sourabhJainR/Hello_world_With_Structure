import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness'))
from state_validator import validate_state


class StateValidatorTests(unittest.TestCase):
    def test_rejects_incomplete_state(self):
        errors = validate_state({'schema_version': '1.0'})
        self.assertTrue(errors)

    def test_accepts_minimal_valid_state(self):
        state = {
            'schema_version': '1.0',
            'task_id': 'task-1',
            'status': 'investigating',
            'intent': {'goal': 'do work'},
            'contract': {'requirements': [], 'acceptance': [], 'protected_behavior': []},
            'repo_facts': [], 'decisions': [], 'evidence': [],
            'changeset': {}, 'verification': [],
            'outcome': {'status': 'unknown'}, 'open_risks': [], 'next': []
        }
        self.assertEqual(validate_state(state), [])


if __name__ == '__main__':
    unittest.main()
