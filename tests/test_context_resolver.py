import tempfile
import unittest
from pathlib import Path

from portable.agent_capabilities import PersistentMemory
from portable.context_engine import ContextEngine, ContextPolicy
from portable.context_graph import ContextGraph, ContextNode
from portable.context_resolver import ContextResolver


class ContextResolverTests(unittest.TestCase):
    def test_resolves_graph_and_memory_context_under_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("task:1", "task", "Fix timeout", "task", 1.0))
            graph.upsert_node(ContextNode("file:1", "file", "client.py", "repo", 1.0))
            graph.link("task:1", "touches", "file:1", source="repo", confidence=0.9)
            memory.remember("project", "prior", "Previous timeout fix used bounded retry", confidence=0.9, verified=True, approved=True)
            resolver = ContextResolver(memory, graph, ContextEngine(ContextPolicy(max_chars=240, max_items=4, max_item_chars=100, output_chars=240)))
            result = resolver.resolve("Fix timeout", node_id="task:1")
            self.assertTrue(result.pack)
            self.assertIn("client.py", result.pack)
            self.assertTrue(result.digest)
            self.assertLessEqual(len(result.pack), 240)
            memory.close()

    def test_required_context_is_reported_when_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("task:1", "task", "Task", "task"))
            resolver = ContextResolver(memory, graph, ContextEngine(ContextPolicy(max_chars=10, max_items=2, max_item_chars=20, output_chars=20)))
            result = resolver.resolve("Task", node_id="task:1", required=("This required fact cannot fit",))
            self.assertIn("This required fact cannot fit", result.omitted)
            memory.close()

    def test_workspace_scope_is_graph_relationship_not_private_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("task:1", "task", "Task", "task"))
            graph.upsert_node(ContextNode("ws:1", "workspace", "Shared", "workspace"))
            graph.upsert_node(ContextNode("private:1", "note", "Private", "private", 1.0, {"private": True}))
            graph.link("task:1", "in_workspace", "ws:1", source="workspace")
            graph.link("task:1", "related", "private:1", source="private")
            resolver = ContextResolver(memory, graph, ContextEngine(ContextPolicy(max_chars=1000)))
            result = resolver.resolve("Task", node_id="task:1", workspace_id="ws:1")
            self.assertIn("Shared", result.pack)
            self.assertNotIn("Private", result.pack)
            memory.close()
