import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".ai-harness" / "runtime" / "collaboration.py"
spec = importlib.util.spec_from_file_location("collaboration", PATH)
collaboration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(collaboration)


def intent():
    return {"goal": "Fix tenant export filtering", "intent_digest": "intent-123"}


def test_handoff_preserves_intent_and_scope():
    packet = collaboration.build_handoff(
        intent=intent(),
        phase="analysis",
        from_component="legacy",
        to_component="rca",
        findings=[{"text": "Empty list shape takes fallback", "task_scope": "analysis"}],
        decisions=[{"text": "Inspect fallback before patch", "task_scope": "analysis"}],
    )
    result = collaboration.validate_handoff(packet, expected_intent_digest="intent-123", allowed_scope={"analysis", "verification"})
    assert result["passed"]


def test_handoff_rejects_intent_or_scope_drift():
    packet = collaboration.build_handoff(
        intent=intent(), phase="analysis", from_component="legacy", to_component="rca",
        findings=[{"text": "Unrelated cleanup", "task_scope": "cleanup"}],
    )
    result = collaboration.validate_handoff(packet, expected_intent_digest="different", allowed_scope={"analysis"})
    assert "intent_mismatch" in result["reasons"]
    assert "scope_violation" in result["reasons"]


def test_memory_graph_keeps_lineage():
    first = collaboration.create_memory_item(
        kind="evidence", text="stack trace points to export fallback", source="rca",
        evidence_ids=["ev-1"], confidence=0.9, intent_digest="intent-123"
    )
    second = collaboration.create_memory_item(
        kind="decision", text="test fallback shape", source="planner",
        evidence_ids=["ev-1"], confidence=0.8, intent_digest="intent-123", parents=[first["id"]]
    )
    graph = collaboration.memory_graph([first, second])
    assert second["id"] in graph["nodes"]
    assert any(edge["relation"] == "derived_from" for edge in graph["edges"])


def test_facts_require_evidence():
    item = collaboration.create_memory_item(kind="fact", text="filter is broken", source="rca", confidence=0.8)
    result = collaboration.validate_memory_item(item)
    assert "missing_evidence" in result["reasons"]
