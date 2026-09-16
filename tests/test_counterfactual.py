import tempfile
import unittest
from pathlib import Path

from portable.causal_model import CausalLink, CausalModel
from portable.context_graph import ContextGraph, ContextNode
from portable.counterfactual import CounterfactualEngine, CounterfactualQuery
from portable.persistent_memory import PersistentMemory


class CounterfactualTests(unittest.TestCase):
    def test_intervention_predicts_reachable_effects_without_mutating_world(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            graph = ContextGraph(memory, "demo")
            for node in (ContextNode("demand", "fact", "Demand", "source", 0.9),
                         ContextNode("capacity", "fact", "Capacity", "source", 0.9),
                         ContextNode("latency", "fact", "Latency", "source", 0.9)):
                graph.upsert_node(node)
            causal = CausalModel(graph)
            causal.record(CausalLink("l1", "demand", "capacity", "load", "test", 0.8, ("e1",)))
            causal.record(CausalLink("l2", "capacity", "latency", "queue", "test", 0.7, ("e2",)))
            engine = CounterfactualEngine(causal)
            result = engine.evaluate(CounterfactualQuery(("demand",), ("latency",)))
            self.assertTrue(result.reaches_target)
            self.assertEqual(result.paths, (("demand", "capacity", "latency"),))
            self.assertAlmostEqual(result.confidence, 0.7)
            self.assertEqual(result.interventions, ("demand",))

    def test_missing_target_or_intervention_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            graph = ContextGraph(memory, "demo")
            graph.upsert_node(ContextNode("a", "fact", "A", "source", 1.0))
            causal = CausalModel(graph)
            engine = CounterfactualEngine(causal)
            with self.assertRaises(KeyError):
                engine.evaluate(CounterfactualQuery(("missing",), ("a",)))
            with self.assertRaises(KeyError):
                engine.evaluate(CounterfactualQuery(("a",), ("missing",)))

    def test_cycles_are_bounded_and_target_is_not_reported_without_a_causal_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            graph = ContextGraph(memory, "demo")
            for node_id in ("a", "b", "c"):
                graph.upsert_node(ContextNode(node_id, "fact", node_id, "source", 1.0))
            causal = CausalModel(graph)
            causal.record(CausalLink("l1", "a", "b", "step", "test", 0.8, ("e1",)))
            causal.record(CausalLink("l2", "b", "a", "step", "test", 0.8, ("e2",)))
            engine = CounterfactualEngine(causal)
            result = engine.evaluate(CounterfactualQuery(("a",), ("c",), max_hops=4))
            self.assertFalse(result.reaches_target)
            self.assertEqual(result.paths, ())


if __name__ == "__main__":
    unittest.main()
