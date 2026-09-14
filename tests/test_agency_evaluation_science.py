import pytest

from portable.agency_evaluation_science import paired_delta, select_candidate, summarize


def test_summary_reports_confidence_interval():
    summary = summarize("quality", [0.8, 0.9, 1.0])
    assert summary.count == 3
    assert summary.confidence_low <= summary.mean <= summary.confidence_high


def test_paired_delta_and_candidate_selection():
    delta = paired_delta([0.7, 0.8], [0.8, 0.9])
    assert delta.mean == pytest.approx(0.1)
    winner, summaries = select_candidate({"a": [0.8, 0.81], "b": [0.9, 0.91]}, minimum_mean=0.85)
    assert winner == "b"
    assert len(summaries) == 2
