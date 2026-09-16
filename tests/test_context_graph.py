from pathlib import Path

from portable.agent_capabilities import PersistentMemory
from portable.context_graph import ContextGraph, ContextNode


def test_node_and_edge_round_trip(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    graph.upsert_node(ContextNode("task:1", "task", "Fix timeout", "test", 0.9))
    graph.upsert_node(ContextNode("file:1", "file", "client.py", "repo", 1.0))
    graph.link("task:1", "touches", "file:1", source="test", confidence=0.8)
    assert graph.get_node("task:1").label == "Fix timeout"
    assert graph.neighbors("task:1")[0].target_id == "file:1"
    memory.close()


def test_duplicate_writes_are_idempotent(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    node = ContextNode("task:1", "task", "Fix timeout", "test", 0.9)
    assert graph.upsert_node(node) == node
    assert graph.upsert_node(node) == node
    assert graph.get_node("task:1") == node
    memory.close()


def test_neighbors_are_deterministic_and_bounded(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    graph.upsert_node(ContextNode("a", "task", "A", "test", 1.0))
    for node_id in ("c", "b", "d"):
        graph.upsert_node(ContextNode(node_id, "file", node_id, "test", 1.0))
        graph.link("a", "touches", node_id, source="test")
    assert [edge.target_id for edge in graph.neighbors("a", limit=2)] == ["b", "c"]
    memory.close()


def test_digest_is_stable(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    graph.upsert_node(ContextNode("a", "task", "A", "test", 1.0))
    graph.upsert_node(ContextNode("b", "file", "B", "test", 1.0))
    graph.link("a", "touches", "b", source="test", confidence=0.7)
    assert graph.digest() == graph.digest()
    memory.close()
