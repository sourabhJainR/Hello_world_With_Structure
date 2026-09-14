from portable.agent_patterns import (
    EvidenceItem,
    MixtureOfAgents,
    OneChangeOptimizer,
    ResearchPlanner,
    RouteRequest,
    ScopeChecker,
    Specialist,
    SpecialistRouter,
)


def test_router_uses_least_privilege_tool_boundary():
    router = SpecialistRouter(
        [
            Specialist("researcher", ("research",), ("fetch", "search"), priority=1),
            Specialist("security", ("security", "review"), ("github", "fetch"), priority=1),
        ]
    )
    decision = router.route(RouteRequest("research repository", ("research",), ("fetch",)))
    assert decision.specialist == "researcher"
    assert decision.tools == ("fetch",)
    assert decision.coverage == 1.0


def test_research_planner_creates_one_bounded_parallel_wave():
    plan = ResearchPlanner().build(["find API contract", "find deployment constraints"])
    assert len(plan.tasks) == 2
    assert plan.waves == (("research-1", "research-2"),)
    assert plan.digest


def test_mixture_of_agents_requires_explicit_judge():
    result = MixtureOfAgents().run(
        ["answer A", "answer B"],
        lambda answers: ("synthesized", [1], 0.75),
        [EvidenceItem("docs", "claim", 0.9)],
    )
    assert result.answer == "synthesized"
    assert result.selected == (1,)
    assert result.agreement == 0.75
    assert result.evidence[0].source == "docs"


def test_one_change_optimizer_keeps_only_improving_change():
    calls = []

    def evaluate(value):
        return {"base": 0.5, "better": 0.8, "worse": 0.4}[value]

    def diagnose(value, score):
        return "improve" if value == "base" else ""

    def mutate(value, diagnosis):
        calls.append((value, diagnosis))
        return "better"

    result = OneChangeOptimizer().optimize(
        "base", evaluate=evaluate, diagnose=diagnose, mutate=mutate, max_rounds=2
    )
    assert result.baseline_score == 0.5
    assert result.final_score == 0.8
    assert result.artifact == "better"
    assert result.rounds[0].kept is True
    assert calls == [("base", "improve")]


def test_scope_checker_flags_unrelated_ci_and_dependency_changes():
    report = ScopeChecker().check(
        "fix parser", ["portable/parser.py", ".github/workflows/ci.yml", "requirements.txt"]
    )
    assert report.likely_creep == 2
    assert report.findings[0].classification == "likely_creep"
    assert report.digest
