from pathlib import Path

from portable.agent_memory import AgentMemory
from portable.learning_steward import LearningSteward
from runtime.task_memory import guidance


def test_agent_memory_is_private_and_bounded(tmp_path: Path):
    memory = AgentMemory(tmp_path, "builder", max_entries=2, max_chars=200)
    memory.remember("first")
    memory.remember("second")
    memory.remember("third")
    text = memory.read()
    assert "third" in text
    assert "first" not in text


def test_learning_steward_records_only_explicit_lessons(tmp_path: Path):
    steward = LearningSteward(tmp_path, run_id="run-1", task="fix build")
    output = """## LEARNINGS
- failed | mvn test | compiler flag unsupported
- worked | use supported compiler flags | deterministic build passes
## OTHER
ignore this
"""
    rows = steward.persist(output, evidence_ids=["agent:verifier"])
    assert len(rows) == 2
    assert "unsupported" in guidance(tmp_path, "fix build")
    assert "deterministic build" in guidance(tmp_path, "fix build")
