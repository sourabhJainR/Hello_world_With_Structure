from pathlib import Path

from portable.agency_observability import Dataset, DatasetItem, Tracer, run_experiment
from portable.agency_trace_export import CompositeTraceExporter, JsonlTraceExporter, apply_regression_score, correlate_trace_with_regression


def test_composite_exporter_fans_out_and_jsonl_round_trips(tmp_path: Path):
    path = tmp_path / "traces.jsonl"
    exporter = CompositeTraceExporter((JsonlTraceExporter(path),))
    tracer = Tracer(exporter)
    trace = tracer.start("task", {"task_id": "t13"})
    trace.finish()
    tracer.exporter.export(trace)
    text = path.read_text()
    assert trace.trace_id in text
    assert '"task_id": "t13"' in text


def test_regression_result_is_correlated_to_trace_and_scored():
    dataset = Dataset("coding-regression", "7", (DatasetItem("a", "A"),))
    regression = run_experiment(
        dataset,
        lambda value: value.upper(),
        lambda item, output: {"correctness": float(output == item.expected)},
    )
    tracer = Tracer()
    trace = tracer.start("task")
    link = correlate_trace_with_regression(trace, "reg-123", regression)
    apply_regression_score(trace, link)
    assert link.trace_id == trace.trace_id
    assert link.regression_id == "reg-123"
    assert link.dataset_digest == dataset.digest
    assert link.passed
    assert trace.metadata["regressions"][0]["regression_id"] == "reg-123"
    assert trace.scores[-1].name == "regression_pass"
    assert trace.scores[-1].value == 1.0


def test_failed_regression_remains_visible_without_overriding_trace_status():
    dataset = Dataset("coding-regression", "8", (DatasetItem("a", "B"),))
    regression = run_experiment(
        dataset,
        lambda value: value.upper(),
        lambda item, output: {"correctness": float(output == item.expected)},
    )
    trace = Tracer().start("task")
    link = correlate_trace_with_regression(trace, "reg-124", regression)
    apply_regression_score(trace, link)
    assert not link.passed
    assert trace.scores[-1].value == 0.0
    assert link.failures
