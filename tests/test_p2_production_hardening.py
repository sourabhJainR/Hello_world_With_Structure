import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from p0 import new_state
from p2 import compare_eval_baseline, memory_is_active, memory_record, predict_change_risk, route_model, save_memory
from p2_pipeline import plan_task, retrieve_memory


class P2ProductionHardeningTests(unittest.TestCase):
    def test_hard_constraints_override_quality(self):
        result = route_model(
            {"requires_reasoning": True, "max_latency_ms": 100, "max_cost_per_1k": 0.2},
            [
                {"name": "deep", "quality": .99, "latency_ms": 500, "cost_per_1k": .1, "capabilities": ["reasoning"]},
                {"name": "fast", "quality": .8, "latency_ms": 90, "cost_per_1k": .2, "capabilities": ["reasoning"]},
            ],
        )
        self.assertEqual(result["selected"], "fast")
        self.assertEqual(result["rejected"][0]["reason"], "constraint-exceeded")

    def test_memory_rejects_secret_like_content(self):
        with self.assertRaises(ValueError):
            memory_record("ops", "api_key=123456789", "test", now=100)

    def test_memory_rejects_invalid_expiry_and_is_bounded(self):
        record = memory_record("ops", "valid observation", "test", ttl_seconds=5, now=100)
        record["expires_at"] = 90
        self.assertFalse(memory_is_active(record, now=100))
        with self.assertRaises(ValueError):
            memory_record("ops", "valid observation", "test", ttl_seconds=-1, now=100)

    def test_memory_persistence_is_atomic_and_validated(self):
        record = memory_record("ops", "valid observation", "test", now=100)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.json"
            save_memory(path, [record])
            self.assertTrue(path.exists())
            self.assertIn('valid observation', path.read_text(encoding='utf-8'))

    def test_pipeline_is_traceable(self):
        state = new_state("T1", "improve export")
        plan_task(state, {"scope": 2, "requires_reasoning": True, "changed_paths": ["src/export.py"]}, [{"name": "m", "quality": .9, "latency_ms": 10, "cost_per_1k": .1, "capabilities": ["reasoning"]}])
        self.assertEqual(len(state["decisions"]), 2)
        self.assertTrue(all(d["evidence_ids"] for d in state["decisions"]))

    def test_memory_pipeline_is_bounded(self):
        state = new_state("T2", "memory")
        records = [memory_record("a", "one", "x", .9, now=100), memory_record("a", "two", "y", .8, now=101)]
        self.assertEqual(len(retrieve_memory(state, records, "a", limit=1, now=101)), 1)
        self.assertEqual(len(state["evidence"]), 1)

    def test_metric_directionality_is_respected(self):
        result = compare_eval_baseline({"accuracy": .95, "latency": 100}, {"accuracy": .95, "latency": 80}, required=["accuracy", "latency"], directions={"accuracy": "higher", "latency": "lower"})
        self.assertTrue(result["promotable"])
        result = compare_eval_baseline({"latency": 100}, {"latency": 120}, required=["latency"], directions={"latency": "lower"})
        self.assertFalse(result["promotable"])

    def test_invalid_metric_direction_fails_closed(self):
        with self.assertRaises(ValueError):
            compare_eval_baseline({"accuracy": .9}, {"accuracy": .91}, directions={"accuracy": "best"})

    def test_risk_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            predict_change_risk(["src/a.py"], coverage=1.1)


if __name__ == '__main__':
    unittest.main()
