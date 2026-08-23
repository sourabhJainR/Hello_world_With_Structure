"""Tests for deterministic IO-aware context selection and session ownership."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".ai-harness" / "context_engine.py"
LAUNCHER = ROOT / ".ai-harness" / "run.py"


class ContextEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("context_engine", MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.module)

    def test_context_respects_budget(self):
        result = self.module.select_context(
            "authentication export",
            "# Repository Context\n" + "- src/authentication/export/service.py\n" * 200,
            "lesson authentication export security\n" * 50,
            "review export should preserve authorization\n" * 50,
            budget_chars=2000,
        )
        total = sum(len(value) for key, value in result.items() if key in {"repository", "memory", "history"})
        self.assertLessEqual(total, 2000)

    def test_strategy_is_explicit(self):
        result = self.module.select_context("feature", "repo", "memory", "history", 1000)
        self.assertIn("stable-prefix", result["strategy"])

    def test_launcher_exists_as_public_entrypoint(self):
        self.assertTrue(LAUNCHER.exists())

    def test_session_allocator_is_idempotent(self):
        spec = importlib.util.spec_from_file_location("run_launcher", LAUNCHER)
        launcher = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(launcher)
        expected = Path(tempfile.gettempdir()) / "ai-harness-test-session"
        original = launcher._original_make_run_dir
        try:
            launcher._session_dir = None
            launcher._original_make_run_dir = lambda: expected
            first = launcher.session_make_run_dir()
            second = launcher.session_make_run_dir()
            self.assertEqual(first, expected)
            self.assertEqual(first, second)
        finally:
            launcher._original_make_run_dir = original
            launcher._session_dir = None


if __name__ == "__main__":
    unittest.main()
