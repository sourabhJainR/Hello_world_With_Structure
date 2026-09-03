import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / ".ai-harness" / "runtime" / "second_brain.py"
spec = importlib.util.spec_from_file_location("second_brain", MODULE)
assert spec and spec.loader
second_brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(second_brain)


class SecondBrainTests(unittest.TestCase):
    def test_memory_requires_provenance_for_learned_items(self):
        item = second_brain.create_memory(
            kind="lesson", text="Prefer focused verification", source="run-1",
            evidence_ids=["verify-1"], confidence=0.9, intent_digest="abc"
        )
        self.assertEqual([], second_brain.validate_memory(item, expected_intent_digest="abc"))
        self.assertIn("missing_evidence", second_brain.validate_memory(
            {**item, "evidence_ids": []}, expected_intent_digest="abc"
        ))

    def test_memory_is_scoped_to_intent(self):
        item = second_brain.create_memory(
            kind="decision", text="Use local adapter", source="run-1",
            evidence_ids=["e1"], intent_digest="abc"
        )
        self.assertIn("intent_mismatch", second_brain.validate_memory(item, expected_intent_digest="xyz"))

    def test_rank_prefers_relevant_high_confidence_memory(self):
        rows = [
            second_brain.create_memory(kind="fact", text="database migration is pending", source="r1", evidence_ids=["e1"], confidence=0.4),
            second_brain.create_memory(kind="fact", text="database tests are green", source="r2", evidence_ids=["e2"], confidence=0.9),
        ]
        ranked = second_brain.rank_memory(rows, query_terms={"database", "tests"}, limit=1)
        self.assertEqual("database tests are green", ranked[0]["text"])

    def test_heartbeat_is_read_only_and_explainable(self):
        result = second_brain.heartbeat_suggestions(
            tasks=[{"title": "Review release", "status": "open"}, {"title": "Done task", "status": "done"}],
            recent_outcomes=[{"text": "previous run failed verification"}],
            now=123,
        )
        self.assertEqual(1, len(result))
        self.assertEqual("suggestion", result[0]["mode"])
        self.assertIn("failure signal", result[0]["reason"])


if __name__ == "__main__":
    unittest.main()
