import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / ".ai-harness/evals/cases.jsonl"
RUNNER = ROOT / "scripts/run_evals.py"


class EvalSuiteTests(unittest.TestCase):
    def test_eval_cases_are_valid_and_cover_required_fields(self):
        cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreaterEqual(len(cases), 12)
        ids = {case["id"] for case in cases}
        self.assertEqual(len(ids), len(cases))
        for case in cases:
            self.assertIn(case["expected_mode"], {"implement", "debug", "research", "poc", "review"})
            self.assertIn("required_capabilities", case)
            self.assertIn("forbidden_capabilities", case)

    def test_eval_runner_is_dependency_free_and_passes(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["policy_failures"], [])
        self.assertTrue(report["release_ready"])


if __name__ == "__main__":
    unittest.main()
