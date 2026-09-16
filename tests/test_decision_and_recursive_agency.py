from portable.decision_fabric import (
    ChoiceDecision,
    DecisionFabric,
    DecisionPolicy,
    DecisionQuestion,
    NoulDecision,
    ScoreDecision,
)
from portable.recursive_agency import RecursiveAgency, WorkItem


def test_decision_fabric_validates_typed_parallel_questions():
    def evaluate(state, question):
        if question.kind == "choice":
            return ChoiceDecision("fix", {"fix": 0.9, "stop": 0.1}, 0.95)
        if question.kind == "score":
            return ScoreDecision("high", {"low": 0.1, "high": 0.9}, 0.9)
        return NoulDecision(0.8, 0.92)

    batch = DecisionFabric(evaluate).evaluate(
        {"failure": "test"},
        [
            DecisionQuestion("route", "choice", options=("fix", "stop")),
            DecisionQuestion("risk", "score", levels=("low", "high")),
            DecisionQuestion("safe", "noul", claim="the change is within scope"),
        ],
    )
    assert batch.decisions["route"].selected == "fix"
    assert batch.decisions["risk"].level == "high"
    assert batch.decisions["safe"].probability_true == 0.8
    assert DecisionPolicy(min_confidence=0.9).gate(action="repair", decision=batch.decisions["route"], require="fix").allowed


def test_recursive_agency_keeps_dependencies_and_stops_on_budget():
    items = [
        WorkItem("research", "research", priority=1),
        WorkItem("build", "build", priority=2, dependencies=("research",)),
        WorkItem("verify", "verify", priority=3, dependencies=("build",)),
    ]
    seen = []

    def build(item):
        seen.append("build:" + item.id)
        return True, ("built:" + item.id,)

    def verify(item):
        return True, 1.0, ("verified:" + item.id,)

    receipt = RecursiveAgency(max_cycles=2).run(
        objective="ship",
        discover=lambda: items,
        build=build,
        verify=verify,
        remember=lambda item, observation: (f"lesson:{item.id}",),
        schedule=lambda remaining: [x.id for x in remaining],
        optimize=lambda cycles: (),
    )
    assert receipt.result == "budget_exhausted"
    assert seen == ["build:research", "build:build"]
    assert receipt.scheduled == ["verify"]
