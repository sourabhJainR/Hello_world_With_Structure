import importlib.util
import tempfile
import unittest
from pathlib import Path

from portable.agency_provenance import ProvenanceLedger


ROOT = Path(__file__).resolve().parents[1]
COLLABORATION_PATH = ROOT / ".ai-harness" / "runtime" / "collaboration.py"
RENDERER_PATH = ROOT / "skills" / "engineering" / "improve-codebase-architecture" / "render_report.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collaboration = load_module("collaboration_under_test", COLLABORATION_PATH)
renderer = load_module("architecture_report_renderer", RENDERER_PATH)


class PhaseHandoffTests(unittest.TestCase):
    def test_handoff_validates_requested_phase_and_round_trips(self):
        packet = collaboration.build_handoff(
            intent={"intent_digest": "intent-123"},
            phase="design",
            requested_phase="implementation",
            from_component="architecture-review",
            to_component="implement",
            scope=["skills/engineering"],
            non_goals=["runtime redesign"],
            context_evidence_digest="ctx-456",
            repository_snapshot="commit-789",
            artifact_ids=["report-1"],
            receipt_ids=["verification-1"],
            parent_provenance_hash="parent-1",
            next_actions=["implement selected candidate"],
        )
        self.assertEqual(
            collaboration.validate_handoff(
                packet,
                expected_intent_digest="intent-123",
                expected_requested_phase="implementation",
            ),
            {"passed": True, "reasons": []},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = collaboration.persist_handoff(Path(tmp), packet)
            loaded = collaboration.load_handoff(
                path,
                expected_intent_digest="intent-123",
                expected_requested_phase="implementation",
            )
        self.assertEqual(loaded["id"], packet["id"])
        self.assertEqual(loaded["context_evidence_digest"], "ctx-456")

    def test_handoff_is_recorded_in_existing_provenance_ledger(self):
        ledger = ProvenanceLedger()
        previous = ledger.append("run-1", "design.completed")
        packet = collaboration.build_handoff(
            intent={"intent_digest": "intent-123"},
            phase="design",
            requested_phase="implementation",
            from_component="design",
            to_component="implement",
            context_evidence_digest="ctx-456",
            repository_snapshot="commit-789",
            parent_provenance_hash=previous.record_hash,
            next_actions=["implement"],
        )
        record = collaboration.record_handoff(ledger=ledger, packet=packet, run_id="run-1")
        self.assertEqual(record.event, "phase.handoff")
        self.assertEqual(record.parent_hash, previous.record_hash)
        ledger.verify()
        self.assertIn("ctx-456", record.detail)


class ArchitectureReportRendererTests(unittest.TestCase):
    def test_renderer_contains_before_after_and_top_recommendation(self):
        data = {
            "repository": "Hello_world_With_Structure",
            "generated_at": "2026-09-14T00:00:00Z",
            "candidates": [{
                "id": "deep-context",
                "title": "Deepen context retrieval",
                "strength": "Strong",
                "dependency": "in-process",
                "files": ["portable/context.py::ContextBroker"],
                "problem": "The interface exposes internal retrieval mechanics.",
                "solution": "Keep retrieval mechanics behind one deep module.",
                "wins": ["locality improves", "interface shrinks"],
                "before_mermaid": "flowchart LR\nA[Caller] --> B[Broker] --> C[Index]",
                "after_mermaid": "flowchart LR\nA[Caller] --> B[Deep context module]",
            }],
            "top_recommendation": "deep-context",
        }
        html = renderer.render(data)
        self.assertIn("BEFORE", html)
        self.assertIn("AFTER", html)
        self.assertIn("Top recommendation", html)
        self.assertIn("Deepen context retrieval", html)


if __name__ == "__main__":
    unittest.main()
