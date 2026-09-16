import tempfile
import unittest
from pathlib import Path

from portable.adaptive_runtime import AdaptiveRuntime
from portable.automation_scheduler import AutomationScheduler
from portable.context_graph import ContextGraph, ContextNode
from portable.persistent_memory import PersistentMemory
from portable.orchestration import Graph
from portable.session_state import SessionStore


class AdaptiveRuntimeContextTests(unittest.TestCase):
    def test_runtime_resolves_context_without_bypassing_orchestrator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            scheduler = AutomationScheduler(root / "automation.db")
            sessions = SessionStore(root / "sessions.db")
            runtime = AdaptiveRuntime(Graph([]), persistent_memory=memory, automation_scheduler=scheduler, session_store=sessions)
            project_key = sessions.project_key(root)
            graph = ContextGraph(memory, project_key)
            graph.upsert_node(ContextNode("task:1", "task", "Fix timeout", "task"))
            graph.upsert_node(ContextNode("file:1", "file", "client.py", "repo"))
            graph.link("task:1", "touches", "file:1", source="repo")
            resolution = runtime.resolve_context(root, "Fix timeout", node_id="task:1")
            self.assertIn("client.py", resolution.pack)
            self.assertTrue(resolution.digest)
            scheduler.close()
            memory.close()
