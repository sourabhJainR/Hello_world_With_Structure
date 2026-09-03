import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness'))
import verification_gate


class VerificationGateTests(unittest.TestCase):
    def test_node_project_without_test_script_is_not_treated_as_verified(self):
        original = verification_gate.ROOT
        with self.subTest('contract'): 
            self.assertFalse(verification_gate.validate_discovery([])[0])
        self.assertTrue(original.exists())

    def test_known_repository_has_a_deterministic_command(self):
        commands = verification_gate.discover_commands()
        self.assertTrue(commands)
        self.assertTrue(all(isinstance(command, list) and command for command in commands))


if __name__ == '__main__':
    unittest.main()
