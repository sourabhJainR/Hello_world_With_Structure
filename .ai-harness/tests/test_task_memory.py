from pathlib import Path

from runtime.task_memory import guidance, record, relevant


def test_failed_command_is_retrievable(tmp_path: Path):
    record(tmp_path, task="fix legacy build", category="command", outcome="failed", detail="compiler flag unsupported", command="mvn test", run_id="run-1")
    rows = relevant(tmp_path, "legacy build")
    assert rows and rows[0]["command"] == "mvn test"
    assert "mvn test" in guidance(tmp_path, "legacy build")


def test_regression_is_distinct_observation(tmp_path: Path):
    row = record(tmp_path, task="fix login timeout", category="regression", outcome="regressed", detail="retry change caused duplicate requests", approach="unbounded retry", run_id="run-2", evidence_ids=["test-7"])
    assert row["status"] == "observation"
    assert relevant(tmp_path, "login timeout")[0]["outcome"] == "regressed"
