import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / ".ai-harness" / "project_profile.py"
PLACEMENT = ROOT / ".ai-harness" / "placement.py"


class ProjectProfileTests(unittest.TestCase):
    def load_module(self, path: Path):
        spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def test_profile_is_language_neutral_and_detects_current_baseline(self) -> None:
        module = self.load_module(PROFILE)
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

    def test_placement_prefers_existing_segregation(self) -> None:
        module = self.load_module(PLACEMENT)
        result = module.build_placement_plan(["ExportService.py", "ExportConstants.py", "ExportHandler.py"])
        self.assertEqual(len(result["recommendations"]), 3)
        for recommendation in result["recommendations"]:
            self.assertTrue(recommendation["preferred"])
            self.assertTrue(recommendation["reason"])


if __name__ == "__main__":
    unittest.main()
