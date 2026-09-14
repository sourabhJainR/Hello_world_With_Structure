from pathlib import Path

from portable.agency_observability import Dataset, DatasetItem, LocalExporter, Tracer, retrieval_scores, run_experiment
from portable.agency_runtime import EvidenceItem, TaskProfile, execute


def test_trace_export_is_local_and_redacts_secrets(tmp_path: Path):
    exporter = LocalExporter(tmp_path / "traces.jsonl", enabled=True)
    tracer = Tracer(exporter)
    trace = tracer.start("task", {"token": "secret-value"})
    span = trace.span("worker", "agent", {"api_key": "abc123"})
    span.score("quality", 0.9, "good")
    span.finish({"authorization": "Bearer abc"})
    tracer.end(trace)
    text = (tmp_path / "traces.jsonl").read_text()
    assert "secret-value" not in text
    assert "abc123" not in text
    assert "Bearer abc" not in text
    assert trace.as_dict()["spans"][0]["scores"][0]["value"] == 0.9


def test_dataset_experiment_is_reproducible():
    dataset = Dataset("coding", "1", (DatasetItem("a", "A"), DatasetItem("b", "B")))
    result = run_experiment(dataset, lambda value: value.upper(), lambda item, output: {"correctness": float(output == item.expected)})
    assert result.passed
    assert result.scores["correctness"] == 1.0
    assert len(result.dataset_digest) == 64


def test_retrieval_scores():
    scores = retrieval_scores(["a.py", "b.py"], ["a.py", "c.py"])
    assert scores == {"precision": 0.5, "recall": 0.5}


def test_execute_emits_trace_id_without_changing_contract(tmp_path: Path):
    tracer = Tracer(LocalExporter(tmp_path / "traces.jsonl", enabled=True))
    task = TaskProfile("t1", "fix login", evidence_required=("source",))

    def worker(task, assignments):
        return {
            "deliverables": ["patch"],
            "verification": ["tests pass"],
            "dimensions": {"correctness": 25, "completeness": 15, "evidence": 15, "verification": 15, "scope_discipline": 10, "security_and_safety": 10, "clarity": 5, "maintainability": 5},
            "hard_gates": {"tests": True},
            "evidence": [EvidenceItem("test", "tests pass")],
        }

    result = execute(task, worker, tracer=tracer)
    assert result.trace_id
    assert result.receipt is not None and result.receipt.passed
    assert "task_quality" in (tmp_path / "traces.jsonl").read_text()
