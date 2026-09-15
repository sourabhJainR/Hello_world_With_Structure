from pathlib import Path

from portable.dream_memory import DreamMemory
from runtime.task_memory import history, record, relevant, revise, guidance


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


def test_dream_promotes_repeated_failure_as_anti_pattern(tmp_path: Path):
    for run in ("run-a", "run-b"):
        record(
            tmp_path,
            task="fix flaky build",
            category="command",
            outcome="failed",
            detail="retrying the unchanged build did not fix the failure",
            command="python build.py",
            approach="repeat unchanged build",
            run_id=run,
            evidence_ids=[f"ci:{run}"],
        )

    promoted = DreamMemory(tmp_path).dream("fix flaky build")
    assert len(promoted) == 1
    assert promoted[0]["promotion"] == "verified"
    assert "ANTI-PATTERN" in promoted[0]["detail"]
    assert "AVOID" in guidance(tmp_path, "fix flaky build").upper()


def test_dream_requires_independent_runs(tmp_path: Path):
    for i in range(3):
        record(
            tmp_path,
            task="same run",
            category="approach",
            outcome="worked",
            detail="one execution retry",
            approach="bounded context",
            run_id="single-run",
            evidence_ids=[f"retry:{i}"],
        )
    assert DreamMemory(tmp_path).dream("same run") == []


def test_dream_keeps_conflicting_outcomes_unpromoted(tmp_path: Path):
    record(tmp_path, task="fix parser", category="bug", outcome="worked", detail="case A", approach="rewrite", run_id="run-1")
    record(tmp_path, task="fix parser", category="bug", outcome="failed", detail="case B", approach="rewrite", run_id="run-2")

    assert DreamMemory(tmp_path).dream("fix parser") == []
    assert all(row["promotion"] == "candidate" for row in relevant(tmp_path, "fix parser"))


def test_revision_preserves_full_history(tmp_path: Path):
    first = record(
        tmp_path,
        task="improve tests",
        category="verification",
        outcome="worked",
        detail="targeted tests caught the regression",
        approach="run targeted tests",
        run_id="r1",
    )
    revised = revise(
        tmp_path,
        first["id"],
        detail="independent CI confirmed the targeted tests",
        promotion="verified",
        evidence_ids=["ci:r2"],
    )
    assert revised["revision"] == 2
    assert revised["supersedes_id"] == first["id"]
    assert len(history(tmp_path, revised["learning_key"])) == 2
