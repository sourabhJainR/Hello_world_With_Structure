from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from portable.agent_memory import AgentMemory
from runtime.task_memory import guidance, record, relevant


def test_private_memory_is_run_scoped(tmp_path: Path):
    AgentMemory(tmp_path, "builder", run_id="run-a").remember("only run a")
    AgentMemory(tmp_path, "builder", run_id="run-b").remember("only run b")
    assert AgentMemory(tmp_path, "builder", run_id="run-a").read() == "only run a"
    assert AgentMemory(tmp_path, "builder", run_id="run-b").read() == "only run b"


def test_learning_is_versioned_and_deduplicated(tmp_path: Path):
    kwargs = dict(task="build api", category="approach", outcome="worked", detail="bounded handoff", approach="explicit contract", run_id="r1", source_agent="learning-steward")
    first = record(tmp_path, **kwargs)
    second = record(tmp_path, **kwargs)
    assert first["schema_version"] == 2
    assert first["learning_version"] == "2.0"
    assert first["id"] == second["id"]
    assert len(relevant(tmp_path, "build api")) == 1


def test_learning_concurrent_writes_remain_valid(tmp_path: Path):
    def write(i: int):
        return record(tmp_path, task="concurrency", category="verification", outcome="worked", detail=f"worker {i}", run_id=f"run-{i}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(write, range(20)))
    assert len(rows) == 20
    assert len(relevant(tmp_path, "concurrency", limit=100)) == 20
    assert "worker 19" in guidance(tmp_path, "concurrency", limit=10000)


def test_private_memory_has_hard_budget(tmp_path: Path):
    memory = AgentMemory(tmp_path, "builder", run_id="run", max_entries=2, max_chars=200)
    memory.remember("a" * 100)
    memory.remember("b" * 100)
    memory.remember("c" * 100)
    rows = memory.snapshot()
    assert len(rows) <= 2
    assert sum(len(str(r["text"])) for r in rows) <= 200
