from portable.local_offload import LocalOffloadBroker, OffloadJob, ResourceBudget


def test_local_offload_runs_safe_command(tmp_path):
    broker = LocalOffloadBroker(tmp_path, budget=ResourceBudget(max_workers=1, timeout_seconds=10))
    result = broker.run(OffloadJob("one", ("python", "-c", "print('ok')")))
    assert result.status == "passed"
    assert "ok" in result.output


def test_local_offload_blocks_mutating_git(tmp_path):
    broker = LocalOffloadBroker(tmp_path, budget=ResourceBudget(max_workers=1, timeout_seconds=10))
    result = broker.run(OffloadJob("one", ("git", "push")))
    assert result.status == "rejected"
    assert "blocked" in (result.error or "")


def test_local_offload_runs_independent_jobs_in_parallel(tmp_path):
    broker = LocalOffloadBroker(tmp_path, budget=ResourceBudget(max_workers=2, timeout_seconds=10))
    jobs = [
        OffloadJob("one", ("python", "-c", "print('one')")),
        OffloadJob("two", ("python", "-c", "print('two')")),
    ]
    results = broker.run_many(jobs)
    assert [r.status for r in results] == ["passed", "passed"]
    assert {r.job_id for r in results} == {"one", "two"}


def test_local_offload_isolates_workspace(tmp_path):
    (tmp_path / "input.txt").write_text("original", encoding="utf-8")
    broker = LocalOffloadBroker(tmp_path, budget=ResourceBudget(max_workers=1, timeout_seconds=10))
    result = broker.run(
        OffloadJob(
            "one",
            ("python", "-c", "from pathlib import Path; Path('input.txt').write_text('changed')"),
            isolate=True,
            allow_write=True,
        )
    )
    assert result.status == "passed"
    assert (tmp_path / "input.txt").read_text(encoding="utf-8") == "original"
