import tempfile
import unittest
from pathlib import Path

from portable.causal_learning import CausalLearner, Intervention, InterventionOutcome
from portable.causal_model import CausalModel
from portable.context_graph import ContextGraph, ContextNode
from portable.counterfactual import CounterfactualEngine, CounterfactualQuery
from portable.persistent_memory import PersistentMemory
from portable.self_model import SelfModel


class CausalLearningTests(unittest.TestCase):
    def _causal(self, directory: str):
        memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
        graph = ContextGraph(memory, "project-x")
        graph.upsert_node(ContextNode("cause", "concept", "cause"))
        graph.upsert_node(ContextNode("effect", "concept", "effect"))
        graph.upsert_node(ContextNode("other", "concept", "other"))
        return memory, CausalModel(graph)

    def test_intervention_outcome_records_empirical_causal_link(self):
        with tempfile.TemporaryDirectory() as directory:
            memory, causal = self._causal(directory)
            learner = CausalLearner(causal)
            learner.propose(Intervention("i1", "cause", True, "effect"))
            link = learner.observe(InterventionOutcome("i1", "effect", True, "e1", 0.9))
            self.assertIsNotNone(link)
            self.assertEqual(link.confidence, 0.9)
            self.assertIn("i1", link.properties.get("interventions", []))

    def test_negative_intervention_is_stored_without_promoting_causal_link(self):
        with tempfile.TemporaryDirectory() as directory:
            _, causal = self._causal(directory)
            learner = CausalLearner(causal)
            learner.propose(Intervention("i1", "cause", False, "effect"))
            self.assertIsNone(learner.observe(InterventionOutcome("i1", "effect", False, "e1", 0.8)))
            self.assertEqual(causal.effects_of("cause"), ())


class CounterfactualAndSelfModelTests(unittest.TestCase):
    def test_counterfactual_simulation_returns_alternate_target_state(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            graph = ContextGraph(memory, "project-x")
            graph.upsert_node(ContextNode("cause", "concept", "cause"))
            graph.upsert_node(ContextNode("effect", "concept", "effect"))
            graph.link("cause", "causes", "effect", source="test", confidence=0.9)
            result = CounterfactualEngine(CausalModel(graph)).simulate(
                CounterfactualQuery(("cause",), ("effect",)),
                initial_state={"effect": "off"},
                transition=lambda state, intervention: {**state, "effect": "on"} if intervention == "cause" else state,
            )
            self.assertEqual(result.alternate_predictions, {"effect": "on"})
            self.assertTrue(result.reaches_target)

    def test_self_model_can_segment_by_context_and_difficulty(self):
        with tempfile.TemporaryDirectory() as directory:
            model = SelfModel(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")
            model.record("a", "parser", success=True, context="repo", difficulty=2)
            model.record("b", "parser", success=False, context="repo", difficulty=8)
            profile = model.profile("parser", context="repo", difficulty=2)
            self.assertEqual(profile.confidence, 1.0)
            self.assertEqual(model.profile("parser", context="repo", difficulty=8).confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
