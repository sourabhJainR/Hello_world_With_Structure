#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.construct_index import build_index, validate_references


def test_index_contains_actual_harness_constructs():
    index = build_index(Path(__file__).resolve().parents[2])
    symbols = {(item["path"], item["name"]) for item in index["constructs"]}
    assert (".ai-harness/runtime/construct_index.py", "build_index") in symbols
    assert (".ai-harness/runtime/agent_turn.py", "AgentTurnStateMachine") in symbols


def test_known_reference_resolves():
    index = build_index(Path(__file__).resolve().parents[2])
    item = next(item for item in index["constructs"] if item["path"] == ".ai-harness/runtime/construct_index.py" and item["name"] == "build_index")
    result = validate_references(f"[${item['id']}]", index)
    assert result["passed"]
    assert result["reference_count"] == 1


def test_unknown_construct_is_not_silently_accepted():
    index = build_index(Path(__file__).resolve().parents[2])
    result = validate_references(".ai-harness/runtime/construct_index.py::DoesNotExist", index)
    assert result["unresolved"] == [".ai-harness/runtime/construct_index.py::DoesNotExist"]
    assert not result["passed"]
