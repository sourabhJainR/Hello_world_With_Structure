import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".ai-harness" / "runtime" / "collaboration.py"
spec = importlib.util.spec_from_file_location("collaboration", PATH)
collaboration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(collaboration)


class CollaborationTests(unittest.TestCase):
    def intent(self):
        return {"goal": "Fix tenant export filtering", "intent_digest": "intent-123"}

    def test_handoff_preserves_intent_and_scope(self):
        packet = collaboration.build_handoff(
            intent=self.intent(), phase="analysis", from_component="legacy", to_component="rca",
            findings=[{"text": "Empty list shape takes fallback", "task_scope": "analysis"}],
            decisions=[{"text": "Inspect fallback before patch", "task_scope": "analysis"}],
        )
        result = collaboration.validate_handoff(
            packet, expected_intent_digest="intent-123", allowed_scope={"analysis", "verification"}
        )
        self.assertTrue(result["passed"])

    def test_handoff_rejects_intent_or_scope_drift(self):
        packet = collaboration.build_handoff(
            intent=self.intent(), phase="analysis", from_component="legacy", to_component="rca",
            findings=[{"text": "Unrelated cleanup", "task_scope": "cleanup"}],
        )
        result = collaboration.validate_handoff(
            packet, expected_intent_digest="different", allowed_scope={"analysis"}
        )
        self.assertIn("intent_mismatch", result["reasons"])
        self.assertIn("scope_violation", result["reasons"])

    def test_memory_graph_keeps_lineage(self):
        first = collaboration.create_memory_item(
            kind="evidence", text="stack trace points to export fallback", source="rca",
            evidence_ids=["ev-1"], confidence=0.9, intent_digest="intent-123"
        )
        second = collaboration.create_memory_item(
            kind="decision", text="test fallback shape", source="planner",
            evidence_ids=["ev-1"], confidence=0.8, intent_digest="intent-123", parents=[first["id"]]
        )
        graph = collaboration.memory_graph([first, second])
        self.assertIn(second["id"], graph["nodes"])
        self.assertTrue(any(edge["relation"] == "derived_from" for edge in graph["edges"]))

    def test_facts_require_evidence(self):
        item = collaboration.create_memory_item(
            kind="fact", text="filter is broken", source="rca", confidence=0.8
        )
        result = collaboration.validate_memory_item(item)
        self.assertIn("missing_evidence", result["reasons"])


if __name__ == "__main__":
    unittest.main()
