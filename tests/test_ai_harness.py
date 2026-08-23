import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".ai-harness" / "run.py"


class AdaptiveHarnessTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_capabilities(self) -> None:
        result = self.run_cli("capabilities")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.split()), {"research", "poc", "grill"})

    def test_heuristic_routing_for_feasibility(self) -> None:
        result = self.run_cli(
            "run",
            "--task",
            "Can we build a proof of concept to test whether WebAssembly is feasible?",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        runs = sorted((ROOT / ".ai-harness" / "runs").glob("*"))
        manifest = json.loads((runs[-1] / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("poc", manifest["route"]["capabilities"])
        self.assertIn("research", manifest["route"]["capabilities"])

    def test_dry_run_creates_route_and_phase_artifacts(self) -> None:
        result = self.run_cli("run", "--task", "Add input validation", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        runs = sorted((ROOT / ".ai-harness" / "runs").glob("*"))
        run_dir = runs[-1]
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 2)
        self.assertTrue((run_dir / "repository-map.md").exists())
        self.assertTrue((run_dir / "route.prompt.md").exists())
        self.assertTrue((run_dir / "implement.prompt.md").exists())

    def test_memory_and_groom_commands(self) -> None:
        self.assertEqual(self.run_cli("memory").returncode, 0)
        result = self.run_cli("groom")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("patterns", payload)
        self.assertIn("trusted", payload)


if __name__ == "__main__":
    unittest.main()
