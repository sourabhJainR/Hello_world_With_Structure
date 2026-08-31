import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness'))
from provider import analysis_only_command, is_analysis_only


class ProviderTests(unittest.TestCase):
    def test_rca_marker_is_analysis_only(self):
        self.assertTrue(is_analysis_only('RCA analysis-only\nFind the root cause.'))
        self.assertTrue(is_analysis_only('Find the root cause of intermittent duplication.'))
        self.assertTrue(is_analysis_only('patch_allowed: false'))
        self.assertFalse(is_analysis_only('Implement the requested feature.'))

    def test_claude_rca_uses_plan_mode(self):
        command = analysis_only_command(['claude', '-p'])
        self.assertEqual(command, ['claude', '--permission-mode', 'plan', '-p'])

    def test_codex_rca_uses_read_only_sandbox(self):
        command = analysis_only_command(['codex', 'exec'])
        self.assertEqual(command, ['codex', 'exec', '--sandbox', 'read-only'])

    def test_gemini_rca_uses_plan_mode(self):
        command = analysis_only_command(['gemini', '-p'])
        self.assertEqual(command, ['gemini', '--approval-mode', 'plan', '-p'])


if __name__ == '__main__':
    unittest.main()
