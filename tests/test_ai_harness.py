import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".ai-harness" / "run.py"


class HarnessTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_workflows_are_discoverable(self) -> None:
        result = self.run_cli("workflows")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("coding:", result.stdout)
        self.assertIn("research:", result.stdout)
        self.assertIn("poc:", result.stdout)
        self.assertIn("grill:", result.stdout)

    def test_capabilities_are_discoverable(self) -> None:
        result = self.run_cli("capabilities")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.split()), {"research", "poc", "grill"})

    def test_dry_run_creates_manifest_and_repo_map(self) -> None:
        before = {p for p in (ROOT / ".ai-harness" / "runs").glob("*")}
        result = self.run_cli(
            "run",
            "--agent", "claude",
            "--task", "Test the harness",
            "--capability", "research",
            "--capability", "grill",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        after = {p for p in (ROOT / ".ai-harness" / "runs").glob("*")}
        created = sorted(after - before)
        self.assertEqual(len(created), 1)

        run_dir = created[0]
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["agent"], "claude")
        self.assertEqual(manifest["capabilities"], ["research", "grill"])
        self.assertTrue((run_dir / "repository-map.md").exists())
        self.assertTrue((run_dir / "research.prompt.md").exists())
        self.assertTrue((run_dir / "grill.prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
