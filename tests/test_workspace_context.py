import tempfile
import unittest
from pathlib import Path

from portable.agent_capabilities import PersistentMemory
from portable.context_graph import ContextGraph, ContextNode
from portable.workspace_context import WorkspaceContext


class WorkspaceContextTests(unittest.TestCase):
    def test_private_context_is_not_shared_without_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("ws:1", "workspace", "Engineering", "workspace"))
            graph.upsert_node(ContextNode("note:1", "note", "Private finding", "private", 0.95, {"private": True}))
            workspace = WorkspaceContext(graph)
            workspace.attach("ws:1", "note:1")
            self.assertEqual(workspace.shared_members("ws:1"), ())
            memory.close()

    def test_promotion_creates_new_shared_summary_with_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("ws:1", "workspace", "Engineering", "workspace"))
            graph.upsert_node(ContextNode("note:1", "note", "Private finding", "private", 0.95, {"private": True}))
            workspace = WorkspaceContext(graph)
            workspace.attach("ws:1", "note:1")
            promoted = workspace.promote("ws:1", "note:1", summary="Verified finding", evidence=("run:1",))
            self.assertEqual(promoted.kind, "shared_summary")
            self.assertEqual(promoted.label, "Verified finding")
            self.assertEqual(promoted.properties["evidence"], ["run:1"])
            members = workspace.shared_members("ws:1")
            self.assertEqual([node.node_id for node in members], [promoted.node_id])
            self.assertNotIn("note:1", [node.node_id for node in members])
            memory.close()

    def test_promotion_requires_evidence_and_workspace_link(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.sqlite", require_approval=False)
            graph = ContextGraph(memory, "project")
            graph.upsert_node(ContextNode("ws:1", "workspace", "Engineering", "workspace"))
            graph.upsert_node(ContextNode("note:1", "note", "Private finding", "private", 0.95, {"private": True}))
            workspace = WorkspaceContext(graph)
            with self.assertRaisesRegex(ValueError, "evidence"):
                workspace.promote("ws:1", "note:1", summary="Finding", evidence=())
            with self.assertRaisesRegex(PermissionError, "attached"):
                workspace.promote("ws:1", "note:1", summary="Finding", evidence=("run:1",))
            memory.close()
