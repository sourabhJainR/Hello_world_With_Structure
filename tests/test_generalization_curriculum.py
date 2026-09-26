from portable.generalization_curriculum import GeneralizationCurriculum, ExperimentResult


def test_curriculum_covers_multiple_families_and_is_deterministic():
    c = GeneralizationCurriculum(max_experiments=6)
    a = c.generate("planner", ["coding", "research"], conditions=["novel", "shift", "compose"])
    b = c.generate("planner", ["coding", "research"], conditions=["novel", "shift", "compose"])
    assert a == b
    assert {x.task_family for x in a} == {"coding", "research"}


def test_generalization_requires_cross_family_success():
    c = GeneralizationCurriculum(max_experiments=6)
    experiments = c.generate("planner", ["coding", "research"], conditions=["novel", "shift"])
    report = c.evaluate(
        "planner",
        experiments,
        lambda e: ExperimentResult(e.id, 0.82, "ev-" + e.id),
        baseline_score=0.80,
    )
    assert report.generalized is True
    assert len(report.family_scores) == 2


def test_generalization_rejects_family_regression():
    c = GeneralizationCurriculum(max_experiments=4)
    experiments = c.generate("planner", ["coding", "research"], conditions=["novel", "shift"])
    def evaluate(e):
        return ExperimentResult(e.id, 0.60 if e.task_family == "research" else 0.90, "ev-" + e.id)
    report = c.evaluate("planner", experiments, evaluate, baseline_score=0.70)
    assert report.generalized is False
    assert any("task families" in reason for reason in report.reasons)


def test_unverified_evidence_cannot_generalize():
    c = GeneralizationCurriculum(max_experiments=4)
    experiments = c.generate("planner", ["coding", "research"], conditions=["novel"])
    report = c.evaluate(
        "planner", experiments,
        lambda e: ExperimentResult(e.id, 0.90, "ev-" + e.id, verified=False),
        baseline_score=0.70,
    )
    assert report.generalized is False
    assert "unverified experiment evidence" in report.reasons
