import importlib.util
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / ".ai-harness"
sys.path.insert(0, str(HARNESS))
SPEC = importlib.util.spec_from_file_location("safe_provider", HARNESS / "safe_provider.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ResponseResilienceTests(unittest.TestCase):
    def test_known_interrupted_response_is_retryable(self):
        self.assertTrue(MODULE._transient_failure("API Error: The response stopped arriving.", 1))

    def test_unrelated_failure_is_not_retryable(self):
        self.assertFalse(MODULE._transient_failure("permission denied", 1))

    def test_success_is_never_retried(self):
        self.assertFalse(MODULE._transient_failure("API Error: The response stopped arriving.", 0))

    def test_continuation_preserves_original_task_and_partial_output(self):
        prompt = "Implement the requested change."
        previous = "We inspected module X and changed module Y."
        recovered = MODULE._continuation_prompt(prompt, previous, 2)
        self.assertIn(prompt, recovered)
        self.assertIn(previous, recovered)
        self.assertIn("Do not restart completed work", recovered)
        self.assertIn("finish the requested response", recovered)


if __name__ == "__main__":
    unittest.main()
