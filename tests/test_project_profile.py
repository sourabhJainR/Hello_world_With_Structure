import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / ".ai-harness" / "project_profile.py"


class ProjectProfileTests(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location("project_profile", PROFILE)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def test_profile_is_language_neutral_and_detects_current_baseline(self) -> None:
        module = self.load_module()
        profile = module.build_profile()
        self.assertIn("python", profile["languages"])
        self.assertIn("unittest", profile["existing_test_markers"])
        self.assertEqual(profile["third_party_policy"], ".ai-harness/DEPENDENCIES.md")

    def test_cli_outputs_valid_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROFILE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("languages", payload)
        self.assertIn("existing_logging_markers", payload)
        self.assertIn("existing_telemetry_markers", payload)


if __name__ == "__main__":
    unittest.main()
