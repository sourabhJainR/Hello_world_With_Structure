from __future__ import annotations

import pytest

from portable.counterfactual_engine import BranchCandidate, CounterfactualEngine


def test_counterfactual_selection_is_deterministic_and_auditable() -> None:
    engine = CounterfactualEngine(min_confidence=0.5, min_margin=0.01)
    state = {"task": "repair", "risk": "normal"}
    branches = [
        BranchCandidate("deep-verify", 0.92, 0.95, 0.35, 0.10, 0.90, 0.40, 0.0, "more independent evidence"),
        BranchCandidate("fast-verify", 0.80, 0.70, 0.20, 0.20, 0.75, 0.20),
    ]
    decision = engine.evaluate(state, branches)
    assert decision.selected == "deep-verify"
    assert not decision.abstained
    assert decision.state_digest
    assert decision.branches[0].name == "deep-verify"
    assert decision.branches[0].utility > decision.branches[1].utility
    assert decision.as_dict()["selected"] == "deep-verify"


def test_low_confidence_abstains_instead_of_forcing_a_branch() -> None:
    engine = CounterfactualEngine(min_confidence=0.90, min_margin=0.01)
    decision = engine.evaluate(
        {"task": "uncertain"},
        [BranchCandidate("a", 0.70, 0.70, confidence=0.60),
         BranchCandidate("b", 0.68, 0.70, confidence=0.60)],
    )
    assert decision.abstained
    assert decision.selected is None
    assert engine.as_choice(decision) is None


def test_close_alternatives_trigger_margin_abstention() -> None:
    engine = CounterfactualEngine(min_confidence=0.5, min_margin=0.5)
    decision = engine.evaluate(
        {},
        [BranchCandidate("a", 0.90, 0.80, cost=0.2, confidence=0.9),
         BranchCandidate("b", 0.89, 0.80, cost=0.2, confidence=0.9)],
    )
    assert decision.abstained
    assert decision.selected is None
    assert "insufficient" in decision.reason


def test_duplicate_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        CounterfactualEngine().evaluate(
            {}, [BranchCandidate("same", 0.8, 0.8), BranchCandidate("same", 0.7, 0.8)]
        )


def test_ties_are_resolved_by_stable_name_order() -> None:
    engine = CounterfactualEngine(min_confidence=0.0, min_margin=0.0)
    decision = engine.evaluate(
        {},
        [BranchCandidate("z", 0.8, 0.8, cost=0.2, confidence=1.0),
         BranchCandidate("a", 0.8, 0.8, cost=0.2, confidence=1.0)],
    )
    assert decision.selected == "a"
