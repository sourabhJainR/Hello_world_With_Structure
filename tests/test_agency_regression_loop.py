from pathlib import Path

from portable.agency_observability import Dataset, DatasetItem, LocalExporter, Tracer
from portable.agency_regression_loop import PromotionPolicy, RegressionPlan, decide_promotion, execute_regression
from portable.agency_runtime import EvidenceItem, TaskProfile, execute


def _worker(task, assignments):
    return {
        "deliverables": ["patch"],
        "verification": ["tests pass"],
        "dimensions": {"correctness": 25, "completeness": 15, "evidence": 15, "verification": 15, "scope_discipline": 10, "security_and_safety": 10, "clarity": 5, "maintainability": 5},
        "hard_gates": {"tests": True},
        "evidence": [EvidenceItem("tests", "tests pass")],
    }


def test_execute_creates_regression_run_and_promotion_decision(tmp_path: Path):
    dataset = Dataset("coding-regression", "14", (DatasetItem("a", "A"), DatasetItem("b", "B")))
    regression = RegressionPlan(
        dataset=dataset,
        execute_case=lambda trace, value: value.upper(),
        judge=lambda trace, item, output: {"correctness": float(output == item.expected)},
    )
    tracer = Tracer(LocalExporter(tmp_path / "traces.jsonl", enabled=True))
    result = execute(
        TaskProfile("t14", "fix login", evidence_required=("source",)),
        _worker,
        tracer=tracer,
        regression_plan=regression,
        promotion_policy=PromotionPolicy(quality_threshold=0.9, promote_on_pass=True),
    )
    assert result.regression_run is not None
    assert result.regression_run.trace_id == result.trace_id
    assert result.regression_run.result.dataset_digest == dataset.digest
    assert result.regression_run.passed
    assert result.regression_link is not None
    assert result.promotion_decision is not None
    assert result.promotion_decision.action == "promote"
    assert "promotion" in result.as_dict()
    text = (tmp_path / "traces.jsonl").read_text()
    assert result.trace_id in text
    assert result.regression_run.regression_id in text


def test_failed_regression_rolls_back_even_with_good_quality():
    dataset = Dataset("coding-regression", "14-fail", (DatasetItem("a", "B"),))
    regression = RegressionPlan(
        dataset=dataset,
        execute_case=lambda trace, value: value.upper(),
        judge=lambda trace, item, output: {"correctness": float(output == item.expected)},
    )
    tracer = Tracer()
    trace = tracer.start("task")
    run = execute_regression(trace, regression, regression_id="reg-fail")
    decision = decide_promotion(quality=1.0, hard_gates={"tests": True}, regression=run)
    assert not run.passed
    assert decision.action == "rollback"
    assert decision.reason == "regression failed"


def test_hard_gate_failure_rolls_back_before_regression_quality():
    dataset = Dataset("coding-regression", "14-gate", (DatasetItem("a", "A"),))
    regression = RegressionPlan(
        dataset=dataset,
        execute_case=lambda trace, value: value.upper(),
        judge=lambda trace, item, output: {"correctness": 1.0},
    )
    run = execute_regression(Tracer().start("task"), regression, regression_id="reg-gate")
    decision = decide_promotion(quality=1.0, hard_gates={"tests": False}, regression=run)
    assert decision.action == "rollback"
    assert decision.reason == "hard gate failed"


def test_quality_below_threshold_enters_shadow():
    dataset = Dataset("coding-regression", "14-shadow", (DatasetItem("a", "A"),))
    regression = RegressionPlan(
        dataset=dataset,
        execute_case=lambda trace, value: value.upper(),
        judge=lambda trace, item, output: {"correctness": 1.0},
    )
    run = execute_regression(Tracer().start("task"), regression, regression_id="reg-shadow")
    decision = decide_promotion(quality=0.5, hard_gates={"tests": True}, regression=run)
    assert decision.action == "shadow"
