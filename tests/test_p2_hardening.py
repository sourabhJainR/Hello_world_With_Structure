import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from p0 import new_state
from p2 import compare_eval_baseline, memory_record, predict_change_risk, route_model, validate_memory_record
from p2_pipeline import plan_task, retrieve_memory, seed_memory


class P2HardeningTests(unittest.TestCase):
    def test_route_hard_constraints_win_over_quality(self):
        result = route_model({"requires_reasoning": True, "max_latency_ms": 100, "max_cost_per_1k": 0.2}, [
            {"name": "expensive", "quality": .99, "latency_ms": 500, "cost_per_1k": .1, "capabilities": ["reasoning"]},
            {"name": "fast", "quality": .8, "latency_ms": 90, "cost_per_1k": .2, "capabilities": ["reasoning"]},
        ])
        self.assertEqual(result["selected"], "fast")

    def test_invalid_memory_never_becomes_active(self):
        self.assertFalse(memory_record("a", "b", "c", now=10) is None)
        self.assertNotEqual(validate_memory_record({}), [])
        self.assertFalse(__import__("p2").memory_is_active({"topic": "a"}, now=10))

    def test_pipeline_adds_traceable_p2_decisions(self):
        state = new_state("T1", "Improve export")
        plan_task(state, {"scope": 2, "requires_reasoning": True, "changed_paths": ["src/export.py"]}, [{"name": "m", "quality": .9, "latency_ms": 10, "cost_per_1k": .1, "capabilities": ["reasoning"]}])
        self.assertIn("p2", state["metadata"])
        self.assertEqual(len(state["decisions"]), 2)
        self.assertTrue(all(d["evidence_ids"] for d in state["decisions"]))

    def test_memory_retrieval_is_bounded_and_recorded(self):
        state = new_state("T2", "Find architecture guidance")
        records = [seed_memory("architecture", "new", "review:2", .9, now=100), seed_memory("architecture", "old", "review:1", .8, now=99)]
        selected = retrieve_memory(state, records, "architecture", limit=1, now=100)
        self.assertEqual([r["content"] for r in selected], ["new"])
        self.assertEqual(len(state["evidence"]), 1)

    def test_risk_inputs_are_bounded(self):
        result = predict_change_risk([], fanout=0, coverage=1, historical_defects=0)
        self.assertEqual(result["level"], "low")
        with self.assertRaises(ValueError):
            predict_change_risk([], coverage=-0.1)

    def test_eval_missing_required_metrics_blocks_promotion(self):
        result = compare_eval_baseline({"accuracy": .9, "safety": .9}, {"accuracy": .95}, required=["accuracy", "safety"])
        self.assertFalse(result["promotable"])
        self.assertEqual(result["missing_required"], ["safety"])


if __name__ == '__main__':
    unittest.main()
