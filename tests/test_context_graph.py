from pathlib import Path

import pytest

from portable.agent_capabilities import PersistentMemory
from portable.context_graph import ContextGraph, ContextNode


def test_node_and_edge_round_trip_and_persistence(tmp_path: Path):
    path = tmp_path / "memory.sqlite"
    memory = PersistentMemory(path, require_approval=False)
    graph = ContextGraph(memory, "project")
    graph.upsert_node(ContextNode("task:1", "task", "Fix timeout", "test", 0.9))
    graph.upsert_node(ContextNode("file:1", "file", "client.py", "repo", 1.0))
    graph.link("task:1", "touches", "file:1", source="test", confidence=0.8, properties={"line": 42})
    assert graph.get_node("task:1").label == "Fix timeout"
    assert graph.neighbors("task:1")[0].target_id == "file:1"
    assert graph.neighbors("file:1", direction="in")[0].source_id == "task:1"
    assert graph.neighbors("task:1", relation="touches")[0].properties == {"line": 42}
    digest = graph.digest()
    memory.close()

    reopened = PersistentMemory(path, require_approval=False)
    graph2 = ContextGraph(reopened, "project")
    assert graph2.digest() == digest
    assert graph2.get_node("task:1").created_at
    reopened.close()


def test_duplicate_writes_are_idempotent(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    node = ContextNode("task:1", "task", "Fix timeout", "test", 0.9, {"priority": 1})
    assert graph.upsert_node(node) == node
    assert graph.upsert_node(node) == node
    updated = graph.upsert_node(ContextNode("task:1", "task", "Fix timeout now", "test", 0.95, {"priority": 2}))
    assert updated.created_at == node.created_at
    assert graph.get_node("task:1").label == "Fix timeout now"
    memory.close()


def test_neighbors_are_deterministic_and_bounded(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project", max_nodes=4, max_edges=2)
    graph.upsert_node(ContextNode("a", "task", "A", "test"))
    for node_id in ("c", "b", "d"):
        graph.upsert_node(ContextNode(node_id, "file", node_id, "test"))
    for node_id in ("c", "b"):
        graph.link("a", "touches", node_id, source="test")
    with pytest.raises(ValueError, match="edge budget"):
        graph.link("a", "touches", "d", source="test")
    assert [edge.target_id for edge in graph.neighbors("a", limit=2)] == ["b", "c"]
    with pytest.raises(ValueError, match="direction"):
        graph.neighbors("a", direction="sideways")
    memory.close()


def test_digest_is_stable_for_same_graph(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "memory.sqlite", require_approval=False)
    graph = ContextGraph(memory, "project")
    graph.upsert_node(ContextNode("a", "task", "A", "test", 1.0))
    graph.upsert_node(ContextNode("b", "file", "B", "test", 1.0))
    graph.link("a", "touches", "b", source="test", confidence=0.7)
    assert graph.digest() == graph.digest()
    memory.close()
