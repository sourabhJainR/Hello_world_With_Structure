import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".ai-harness"))

from runtime.run_journal import append_event, read_events, verify_chain
from portable.agent_capabilities import PersistentMemory
from portable.context_graph import ContextGraph
from portable.run_context_projector import RunContextProjector
from runtime.run_context_bridge import project_verified_journal


class RunContextProjectorTests(unittest.TestCase):
    def test_verified_journal_becomes_idempotent_graph_context(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            append_event(run_dir, "run.start", {"workflow": "adaptive"})
            append_event(run_dir, "phase.start", {"phase": "execute"})
            append_event(run_dir, "provider.finish", {"phase": "execute", "exit_code": 0})
            append_event(run_dir, "run.finish", {"status": "completed"})
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            first = project_verified_journal(run_dir, "run-1", graph)
            second = project_verified_journal(run_dir, "run-1", graph)
            self.assertTrue(first.accepted)
            self.assertEqual(first.digest, second.digest)
            self.assertIsNotNone(graph.get_node("run:run-1"))
            self.assertTrue(graph.neighbors("run:run-1"))
            memory.close()

    def test_corrupt_journal_is_rejected_without_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            append_event(run_dir, "run.start", {})
            journal = run_dir / "execution.journal.jsonl"
            journal.write_text(journal.read_text(encoding="utf-8").replace('"run.start"', '"run.error"'), encoding="utf-8")
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            result = project_verified_journal(run_dir, "run-2", graph)
            self.assertFalse(result.accepted)
            self.assertIsNone(graph.get_node("run:run-2"))
            memory.close()

    def test_sensitive_journal_fields_are_not_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            append_event(run_dir, "run.start", {"workflow": "adaptive", "secret": "do-not-copy"})
            append_event(run_dir, "run.finish", {"status": "completed", "output": "private-output"})
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            result = project_verified_journal(run_dir, "run-3", graph)
            self.assertTrue(result.accepted)
            node = graph.get_node("run:run-3")
            self.assertNotIn("secret", node.properties)
            self.assertNotIn("output", node.properties)
            memory.close()
