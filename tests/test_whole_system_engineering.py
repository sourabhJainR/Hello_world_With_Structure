from portable.whole_system_engineering import (
    ENGINEERING_DOMAINS,
    EngineeringEvaluation,
    WholeSystemEngineeringEvaluator,
)


def test_generate_covers_frontend_backend_and_architecture():
    evaluator = WholeSystemEngineeringEvaluator()
    tasks = evaluator.generate(
        "build a production web application",
        budget=12,
        required_domains=("frontend", "backend", "architecture", "testing"),
    )
    domains = {task.domain for task in tasks}
    assert {"frontend", "backend", "architecture", "testing"} <= domains
    assert len(tasks) <= 12


def test_evaluation_requires_verified_evidence_for_verified_results():
    evaluator = WholeSystemEngineeringEvaluator()
    tasks = evaluator.generate("fix a full stack regression", budget=4)
    results = [
        EngineeringEvaluation(task, 0.9, True, (f"e-{i}",))
        for i, task in enumerate(tasks)
    ]
    coverage = evaluator.evaluate(tasks, lambda task: results[tasks.index(task)])
    assert coverage.verified
    assert coverage.completeness_ratio > 0
    assert coverage.overall_score >= 0.9


def test_low_domain_score_is_missing():
    evaluator = WholeSystemEngineeringEvaluator(domains=("frontend", "backend"))
    tasks = evaluator.generate("ship a web feature", budget=2)
    results = [
        EngineeringEvaluation(tasks[0], 0.95, True, ("front",)),
        EngineeringEvaluation(tasks[1], 0.40, True, ("back",), ("backend regression",)),
    ]
    coverage = evaluator.evaluate(tasks, lambda task: results[tasks.index(task)])
    assert "frontend" in coverage.covered
    assert "backend" in coverage.missing
    assert not coverage.verified


def test_unknown_domain_rejected():
    evaluator = WholeSystemEngineeringEvaluator()
    try:
        evaluator.generate("x", required_domains=("quantum",))
    except ValueError:
        pass
    else:
        raise AssertionError("unknown domain must fail closed")


def test_domain_catalog_is_explicit():
    assert "frontend" in ENGINEERING_DOMAINS
    assert "backend" in ENGINEERING_DOMAINS
    assert "security" in ENGINEERING_DOMAINS
