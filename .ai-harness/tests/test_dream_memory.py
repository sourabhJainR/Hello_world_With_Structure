from pathlib import Path

from portable.dream_memory import DreamMemory
from runtime.task_memory import record, relevant


def test_dream_promotes_repeated_success_and_is_idempotent(tmp_path: Path):
    for run in ("run-1", "run-2"):
        record(
            tmp_path,
            task="fix cache invalidation",
            category="approach",
            outcome="worked",
            detail="invalidate after commit",
            approach="post-commit invalidation",
            run_id=run,
            evidence_ids=[f"test-{run}"],
        )

    dream = DreamMemory(tmp_path)
    promoted = dream.dream("fix cache invalidation")
    assert len(promoted) == 1
    assert promoted[0]["promotion"] == "verified"
    assert dream.dream("fix cache invalidation") == []


def test_dream_keeps_conflicting_outcomes_unpromoted(tmp_path: Path):
    record(tmp_path, task="fix parser", category="bug", outcome="worked", detail="case A", approach="rewrite", run_id="run-1")
    record(tmp_path, task="fix parser", category="bug", outcome="failed", detail="case B", approach="rewrite", run_id="run-2")

    assert DreamMemory(tmp_path).dream("fix parser") == []
    assert all(row["promotion"] == "candidate" for row in relevant(tmp_path, "fix parser"))
