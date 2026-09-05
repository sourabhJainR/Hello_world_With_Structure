import unittest

from portable.orchestration import Graph, Node, NodeKind, NodeStatus, Orchestrator, RunStatus


class OrchestrationTests(unittest.TestCase):
    def test_graph_rejects_cycles(self):
        nodes = [
            Node("a", NodeKind.DETERMINISTIC, lambda _: 1, depends_on=("b",)),
            Node("b", NodeKind.DETERMINISTIC, lambda _: 1, depends_on=("a",)),
        ]
        with self.assertRaises(ValueError):
            Graph(nodes)

    def test_graph_executes_dependencies_before_dependents(self):
        seen = []
        graph = Graph([
            Node("build", NodeKind.AGENT, lambda _: seen.append("build") or "ok"),
            Node("verify", NodeKind.EVALUATOR, lambda state: seen.append("verify") or state["build"] == "ok", depends_on=("build",)),
        ])
        run = Orchestrator(graph).run("task-1", "ship the change")
        self.assertEqual(run.status, RunStatus.ACCEPTED)
        self.assertEqual(seen, ["build", "verify"])
        self.assertTrue(run.intent_digest)

    def test_agent_loop_requires_evidence_and_bounds_retries(self):
        attempts = []
        graph = Graph([
            Node(
                "agent",
                NodeKind.AGENT,
                lambda _: attempts.append(len(attempts) + 1) or "bad",
                max_attempts=3,
                evaluator=lambda output: output == "good",
                repair=lambda output, _: "good",
            )
        ])
        run = Orchestrator(graph).run("task-2", "fix regression")
        result = run.results["agent"]
        self.assertEqual(run.status, RunStatus.FAILED)
        self.assertEqual(result.status, NodeStatus.FAILED)
        self.assertEqual(result.attempts, 3)
        self.assertGreaterEqual(result.repair_count, 1)
        self.assertGreaterEqual(len(result.evidence), 3)

    def test_self_improvement_is_proposal_only(self):
        graph = Graph([
            Node("agent", NodeKind.AGENT, lambda _: "ok", evaluator=lambda _: True)
        ])
        run = Orchestrator(graph).run("task-3", "implement feature")
        self.assertEqual(run.status, RunStatus.ACCEPTED)
        self.assertEqual(run.learned_candidates, [])

    def test_replay_is_deterministic_and_does_not_execute_nodes(self):
        calls = []
        graph = Graph([
            Node("agent", NodeKind.AGENT, lambda _: calls.append(1) or "ok")
        ])
        orchestrator = Orchestrator(graph)
        run = orchestrator.run("task-4", "verify replay")
        before = len(calls)
        first = orchestrator.replay_json(run)
        second = orchestrator.replay_json(run)
        self.assertEqual(first, second)
        self.assertEqual(before, len(calls))


if __name__ == "__main__":
    unittest.main()
