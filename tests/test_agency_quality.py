import pytest

from portable.agency_quality import ReviewFinding, evaluate, score_dimensions


RUBRIC = {
    "release_threshold": 90,
    "dimensions": {
        "correctness": 25,
        "completeness": 15,
        "evidence": 15,
        "verification": 15,
        "scope_discipline": 10,
        "security_and_safety": 10,
        "clarity": 5,
        "maintainability": 5,
    },
}


def test_score_dimensions_caps_values():
    assert score_dimensions({"correctness": 25, "completeness": 15}, RUBRIC) == 40


def test_score_dimensions_rejects_unknown_dimension():
    with pytest.raises(ValueError):
        score_dimensions({"not_in_rubric": 1}, RUBRIC)


def test_receipt_requires_score_gates_and_no_material_findings():
    receipt = evaluate(
        {name: cap for name, cap in RUBRIC["dimensions"].items()},
        {"acceptance": True, "verification": True},
        rubric=RUBRIC,
    )
    assert receipt.passed

    blocked = evaluate(
        {name: cap for name, cap in RUBRIC["dimensions"].items()},
        {"acceptance": True, "verification": True},
        [ReviewFinding("material", "API behavior is not backward compatible")],
        rubric=RUBRIC,
    )
    assert not blocked.passed


def test_finding_severity_is_validated():
    with pytest.raises(ValueError):
        ReviewFinding("critical", "bad")
