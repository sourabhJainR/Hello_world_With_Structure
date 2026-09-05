from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("regression_memory", ROOT / ".ai-harness" / "runtime" / "regression_memory.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
RegressionKnowledge = MODULE.RegressionKnowledge
RegressionMemory = MODULE.RegressionMemory


def test_unverified_knowledge_is_not_active(tmp_path: Path) -> None:
    memory = RegressionMemory(tmp_path / "regression.db")
    item = RegressionKnowledge("", "bug", component="orchestration", failure_signature="side-effect", invariant="candidate-not-executed", confidence=0.95, test_pointer="tests/test_x.py", evidence_pointer="run-1")
    memory.record(item, verified=False)
    assert memory.retrieve(task_family="bug") == []
    assert memory.stats() == {"total": 1, "active": 0, "pending": 1}


def test_verified_knowledge_is_retrieved_and_ranked_exactly(tmp_path: Path) -> None:
    memory = RegressionMemory(tmp_path / "regression.db")
    exact = RegressionKnowledge("", "story", component="orchestration", failure_signature="candidate-not-executed", invariant="no-import-execution", confidence=0.95, test_pointer="tests/test_x.py", evidence_pointer="run-2")
    family = RegressionKnowledge("family", "story", component="planner", invariant="bounded-context", confidence=0.90, test_pointer="tests/test_y.py", evidence_pointer="run-3")
    memory.record(exact, verified=True)
    memory.record(family, verified=True)
    rows = memory.retrieve(task_family="story", component="orchestration", failure_signature="candidate-not-executed", invariant="no-import-execution")
    assert rows[0].failure_signature == "candidate-not-executed"
    assert memory.stats() == {"total": 2, "active": 2, "pending": 0}
