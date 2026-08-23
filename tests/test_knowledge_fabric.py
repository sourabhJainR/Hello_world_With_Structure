"""Tests for optional structural knowledge integrations."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".ai-harness" / "knowledge_fabric.py"


class KnowledgeFabricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("knowledge_fabric", MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.module)

    def test_disabled_sources_are_advisory(self):
        result = self.module.collect(
            "authentication timeout",
            {
                "knowledge": {
                    "graphify": {"enabled": False},
                    "code_memory": {"enabled": False},
                    "budget_chars": 1000,
                }
            },
        )
        self.assertEqual(result["sources"], [])
        self.assertIn("No external", result["evidence"])

    def test_knowledge_budget_is_bounded(self):
        result = self.module.collect(
            "authentication",
            {
                "knowledge": {
                    "graphify": {"enabled": False},
                    "code_memory": {"enabled": False},
                    "budget_chars": 120,
                }
            },
        )
        self.assertLessEqual(len(result["evidence"]), 120)


if __name__ == "__main__":
    unittest.main()
