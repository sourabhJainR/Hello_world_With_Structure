import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT / ".ai-harness" / "worktree.py"
REVIEWERS = ROOT / ".ai-harness" / "review_agents.py"


class ExecutionExtensionTests(unittest.TestCase):
    def run_cli(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_worktree_script_lists_current_worktrees(self) -> None:
        result = self.run_cli(WORKTREE, "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, list)
        self.assertTrue(any(item.get("worktree") == str(ROOT) for item in payload))

    def test_worktree_name_is_safe(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("worktree", WORKTREE)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertEqual(module.safe_name("feature / auth: v2"), "feature-auth-v2")

    def test_reviewer_dry_run_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            result = self.run_cli(
                REVIEWERS,
                "--agent", "claude",
                "--workspace", str(ROOT),
                "--run-dir", str(run_dir),
                "--task", "Review the current implementation",
                "--review", "correctness",
                "--review", "security",
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((run_dir / "review-correctness.prompt.md").exists())
            self.assertTrue((run_dir / "review-security.prompt.md").exists())
            payload = json.loads((run_dir / "independent-reviews.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 2)
            self.assertTrue(all(item["exit_code"] == 0 for item in payload))


if __name__ == "__main__":
    unittest.main()
