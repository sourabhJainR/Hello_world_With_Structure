import os
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness'))
from security_gate import SecurityGateError, safe_environment, validate_prompt_file, validate_provider_command


class SecurityGateTests(unittest.TestCase):
    def test_only_known_provider_is_allowed(self):
        with self.assertRaises(SecurityGateError):
            validate_provider_command(['bash', '-c', 'echo unsafe'])

    def test_dangerous_permission_override_is_rejected(self):
        with self.assertRaises(SecurityGateError):
            validate_provider_command(['claude', '--dangerously-skip-permissions', '-p'])

    def test_analysis_only_requires_read_only_capability(self):
        validate_provider_command(['codex', 'exec', '--sandbox', 'read-only'], analysis_only=True)
        with self.assertRaises(SecurityGateError):
            validate_provider_command(['codex', 'exec', '--sandbox', 'workspace-write'], analysis_only=True)

    def test_prompt_must_be_under_run_root(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            prompt = Path(root) / 'prompt.md'
            prompt.write_text('task', encoding='utf-8')
            self.assertEqual(validate_prompt_file(prompt, expected_root=Path(root)), prompt.resolve())
            outside = Path(other) / 'prompt.md'
            outside.write_text('task', encoding='utf-8')
            with self.assertRaises(SecurityGateError):
                validate_prompt_file(outside, expected_root=Path(root))

    def test_secret_like_environment_is_not_forwarded(self):
        old = os.environ.get('UNRELATED_SECRET')
        os.environ['UNRELATED_SECRET'] = 'hidden'
        try:
            self.assertNotIn('UNRELATED_SECRET', safe_environment())
        finally:
            if old is None:
                os.environ.pop('UNRELATED_SECRET', None)
            else:
                os.environ['UNRELATED_SECRET'] = old


if __name__ == '__main__':
    unittest.main()
