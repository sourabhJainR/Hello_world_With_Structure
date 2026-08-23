"""Targeted tests for deterministic IO-aware context selection."""
import unittest
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".ai-harness" / "context_engine.py"


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


if __name__ == "__main__":
    unittest.main()
