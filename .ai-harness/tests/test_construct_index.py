#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.construct_index import build_index, validate_references


class ConstructIndexTests(unittest.TestCase):
    def test_index_contains_actual_harness_constructs(self):
        index = build_index(Path(__file__).resolve().parents[2])
        symbols = {(item["path"], item["name"]) for item in index["constructs"]}
        self.assertIn(
            (".ai-harness/runtime/construct_index.py", "build_index"),
            symbols,
        )
        self.assertIn(
            (".ai-harness/runtime/agent_turn.py", "AgentTurnStateMachine"),
            symbols,
        )

    def test_known_reference_resolves(self):
        index = build_index(Path(__file__).resolve().parents[2])
        item = next(
            item
            for item in index["constructs"]
            if item["path"] == ".ai-harness/runtime/construct_index.py"
            and item["name"] == "build_index"
        )
        result = validate_references(f"[${item['id']}]", index)
        self.assertTrue(result["passed"])
        self.assertEqual(result["reference_count"], 1)

    def test_unknown_construct_is_not_silently_accepted(self):
        index = build_index(Path(__file__).resolve().parents[2])
        result = validate_references(
            ".ai-harness/runtime/construct_index.py::DoesNotExist", index
        )
        self.assertEqual(
            result["unresolved"],
            [".ai-harness/runtime/construct_index.py::DoesNotExist"],
        )
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
