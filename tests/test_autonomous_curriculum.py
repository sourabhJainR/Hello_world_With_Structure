from pathlib import Path

import pytest

from portable.autonomous_curriculum import AutonomousCurriculumDiscovery
from portable.persistent_memory import PersistentMemory


def make_discovery(tmp_path: Path) -> AutonomousCurriculumDiscovery:
    memory = PersistentMemory(tmp_path / "memory.sqlite3", require_approval=False)
    return AutonomousCurriculumDiscovery(memory, "demo")


def test_selection_is_deterministic_and_budgeted(tmp_path):
    discovery = make_discovery(tmp_path)
    first = discovery.discover(
        "planner",
        ["search", "reasoning", "verification"],
        uncertainty={"search": 0.9, "reasoning": 0.4, "verification": 0.7},
        budget=3,
    )
    second = discovery.discover(
        "planner",
        ["search", "reasoning", "verification"],
        uncertainty={"search": 0.9, "reasoning": 0.4, "verification": 0.7},
        budget=3,
    )
    assert [(x.task_family, x.condition) for x in first.selected] == [
        (x.task_family, x.condition) for x in second.selected
    ]
    assert len(first.selected) == 3
    assert {x.task_family for x in first.selected} == {"search", "reasoning", "verification"}


def test_unresolved_failures_raise_priority(tmp_path):
    discovery = make_discovery(tmp_path)
    before = discovery.discover(
        "planner", ["search", "verification"], uncertainty={"search": 0.5, "verification": 0.5}, budget=2
    )
    target = before.selected[0]
    discovery.record_outcome("planner", target.task_family, target.condition, score=0.2)
    after = discovery.discover(
        "planner", ["search", "verification"], uncertainty={"search": 0.5, "verification": 0.5}, budget=2
    )
    chosen = next(x for x in after.candidates if (x.task_family, x.condition) == (target.task_family, target.condition))
    assert chosen.failure_rate > 0
    assert chosen.priority > 0


def test_verified_success_reduces_repeated_probe_priority(tmp_path):
    discovery = make_discovery(tmp_path)
    before = discovery.discover(
        "planner", ["search", "verification"], uncertainty={"search": 0.8, "verification": 0.8}, budget=2
    )
    target = before.selected[0]
    for _ in range(3):
        discovery.record_outcome("planner", target.task_family, target.condition, score=0.98)
    after = discovery.discover(
        "planner", ["search", "verification"], uncertainty={"search": 0.8, "verification": 0.8}, budget=2
    )
    chosen = next(x for x in after.candidates if (x.task_family, x.condition) == (target.task_family, target.condition))
    assert chosen.historical_count == 3
    assert chosen.expected_information_gain < target.expected_information_gain


def test_invalid_inputs_are_rejected(tmp_path):
    discovery = make_discovery(tmp_path)
    with pytest.raises(ValueError):
        discovery.discover("planner", ["search"], budget=2)
    with pytest.raises(ValueError):
        discovery.discover("planner", ["search", "verification"], uncertainty={"search": 1.5}, budget=2)
