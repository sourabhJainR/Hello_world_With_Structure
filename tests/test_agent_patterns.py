import unittest

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


class AgentPatternTests(unittest.TestCase):
    def test_router_uses_least_privilege_tool_boundary(self):
        router = SpecialistRouter([
            Specialist("researcher", ("research",), ("fetch", "search"), priority=1),
            Specialist("security", ("security", "review"), ("github", "fetch"), priority=1),
        ])
        decision = router.route(RouteRequest("research repository", ("research",), ("fetch",)))
        self.assertEqual(decision.specialist, "researcher")
        self.assertEqual(decision.tools, ("fetch",))
        self.assertEqual(decision.coverage, 1.0)

    def test_router_fails_closed_on_partial_single_specialist_coverage(self):
        router = SpecialistRouter([
            Specialist("research", ("research",), ("search",)),
            Specialist("security", ("security",), ("review",)),
        ])
        with self.assertRaises(RuntimeError):
            router.route(RouteRequest("research and security", ("research", "security")))

    def test_router_many_uses_bounded_set_cover(self):
        router = SpecialistRouter([
            Specialist("research", ("research", "search"), ("web",), priority=1),
            Specialist("security", ("security",), ("review",), priority=1),
            Specialist("general", ("research", "security"), ("web", "review"), priority=0),
        ])
        decisions = router.route_many(RouteRequest("research security", ("research", "security")))
        self.assertEqual([item.specialist for item in decisions], ["general"])
        self.assertEqual(decisions[0].coverage, 1.0)

    def test_research_planner_creates_dependency_aware_waves(self):
        plan = ResearchPlanner().build(
            ["find API contract", "find deployment constraints", "compare alternatives"],
            dependencies={"compare alternatives": ("research-1", "research-2")},
        )
        self.assertEqual(plan.waves, (("research-1", "research-2"), ("research-3",)))
        self.assertTrue(plan.digest)

    def test_research_planner_rejects_cycles(self):
        with self.assertRaises(ValueError):
            ResearchPlanner().build(
                ["a", "b"],
                dependencies={"a": ("research-2",), "b": ("research-1",)},
            )

    def test_mixture_of_agents_requires_explicit_judge(self):
        result = MixtureOfAgents().run(
            ["answer A", "answer B"],
            lambda answers: ("synthesized", [1], 0.75),
            [EvidenceItem("docs", "claim", 0.9)],
        )
        self.assertEqual(result.answer, "synthesized")
        self.assertEqual(result.selected, (1,))
        self.assertEqual(result.agreement, 0.75)
        self.assertEqual(result.evidence[0].source, "docs")

    def test_evidence_validates_confidence(self):
        with self.assertRaises(ValueError):
            EvidenceItem("docs", "claim", 1.1)

    def test_one_change_optimizer_keeps_only_improving_change(self):
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
        self.assertEqual(result.baseline_score, 0.5)
        self.assertEqual(result.final_score, 0.8)
        self.assertEqual(result.artifact, "better")
        self.assertTrue(result.rounds[0].kept)
        self.assertEqual(calls, [("base", "improve")])

    def test_scope_checker_flags_unrelated_ci_and_dependency_changes(self):
        report = ScopeChecker().check(
            "fix parser", ["portable/parser.py", ".github/workflows/ci.yml", "requirements.txt"]
        )
        self.assertEqual(report.likely_creep, 2)
        self.assertEqual(report.findings[0].classification, "likely_creep")
        self.assertTrue(report.digest)


if __name__ == "__main__":
    unittest.main()
