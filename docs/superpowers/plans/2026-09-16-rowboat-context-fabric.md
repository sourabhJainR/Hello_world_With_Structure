# Rowboat Context Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a durable, provenance-aware context graph using the existing AER memory database so future context can accumulate relationships without creating a second orchestration or memory owner.

**Architecture:** Extend `PersistentMemory` with canonical graph tables and a small `ContextGraph` facade. `StateGraph`, `TaskPlan`, `CapabilityFabric`, and existing context packing remain unchanged. The graph is a bounded projection of durable context, not an execution engine.

**Tech Stack:** Python standard library, SQLite/WAL, pytest, existing AER portable runtime.

**Spec:** `docs/ROWBOAT_ADAPTATION_SPEC.md`

## Global Constraints

- No paid service or new third-party runtime dependency.
- `PersistentMemory` remains the sole durable memory owner.
- Graph traversal is deterministic and bounded.
- Graph records retain provenance, confidence, and timestamps.
- Existing orchestration and safety gates remain authoritative.

---

### Task 1: Define graph contracts and regression tests

**Files:**
- Create: `tests/test_context_graph.py`
- Modify: `portable/agent_capabilities.py`
- Create: `portable/context_graph.py`

**Interfaces:**
- `ContextNode(node_id, kind, label, source, confidence, properties)` is immutable.
- `ContextEdge(edge_id, source_id, relation, target_id, source, confidence, properties)` is immutable.
- `ContextGraph(memory, project)` exposes `upsert_node`, `get_node`, `link`, `neighbors`, and `digest`.
- `PersistentMemory` provides private canonical SQLite access to graph tables through its existing connection/lock ownership.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from portable.agent_capabilities import PersistentMemory
from portable.context_graph import ContextEdge, ContextGraph, ContextNode


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
    graph.upsert_node(node)
    graph.upsert_node(node)
    graph.link("task:1", "relates", "task:1b", source="test") if False else None
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
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `pytest -q tests/test_context_graph.py`
Expected: FAIL because `portable.context_graph` does not yet exist.

- [ ] **Step 3: Implement the minimal graph contracts**

Use dataclasses with validation for non-empty identifiers/kinds/labels, confidence in `[0, 1]`, and mapping properties. Add SQLite tables to `PersistentMemory` using the same `_lock` and `_connect()` path. Store JSON properties canonically with sorted keys.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run: `pytest -q tests/test_context_graph.py`
Expected: PASS.

- [ ] **Step 5: Run the existing memory tests**

Run: `pytest -q tests/test_agency_agent_capabilities.py tests/test_aer_core_runtime_services.py`
Expected: PASS with no behavioral regressions.

- [ ] **Step 6: Commit the implementation**

```bash
git add portable/agent_capabilities.py portable/context_graph.py tests/test_context_graph.py
git commit -m "feat: add durable context graph"
```

### Task 2: Review, CI, and merge Slice 1

**Files:**
- Review: PR diff and CI results only unless findings require source changes.

- [ ] **Step 1: Open the PR against `main`.**
- [ ] **Step 2: Review the diff for ownership, determinism, bounds, security, and compatibility.**
- [ ] **Step 3: Fix every actionable finding on the same branch.**
- [ ] **Step 4: Wait for every required GitHub check to finish; do not stop at the first green check.**
- [ ] **Step 5: Merge only after all checks are green and review findings are resolved.**
- [ ] **Step 6: Start the next backlog slice from the newly merged `main`.**
