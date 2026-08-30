import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / '.ai-harness' / 'runtime'))
from p2 import compare_eval_baseline, memory_is_active, memory_record, predict_change_risk, route_model, select_memory


class P2RuntimeTests(unittest.TestCase):
    def test_model_routing_prefers_quality_for_complex_work(self):
        result = route_model(
            {"scope": 3, "blast_radius": 2, "uncertainty": 2, "requires_code": True, "requires_reasoning": True},
            [
                {"name": "fast", "quality": 0.7, "latency_ms": 200, "cost_per_1k": 0.1, "fast": True, "capabilities": ["code", "reasoning"]},
                {"name": "deep", "quality": 0.95, "latency_ms": 900, "cost_per_1k": 0.8, "capabilities": ["code", "reasoning"]},
            ],
        )
        self.assertEqual(result["selected"], "deep")

    def test_model_routing_rejects_incompatible_provider(self):
        result = route_model({"requires_code": True}, [{"name": "chat", "quality": 1, "capabilities": ["reasoning"]}])
        self.assertIsNone(result["selected"])
        self.assertEqual(result["reason"], "no-compatible-model")

    def test_memory_has_provenance_and_expiry(self):
        record = memory_record("architecture", "uses ports", "review:42", 0.9, ttl_seconds=10, tags=["architecture", "verified"])
        self.assertEqual(record["source"], "review:42")
        self.assertTrue(memory_is_active(record, record["created_at"] + 9))
        self.assertFalse(memory_is_active(record, record["created_at"] + 10))

    def test_memory_selection_is_deterministic_and_bounded(self):
        records = [
            memory_record("a", "low", "x", 0.4),
            memory_record("a", "high", "y", 0.9),
            memory_record("b", "other", "z", 1.0),
        ]
        selected = select_memory(records, "a", now=max(r["created_at"] for r in records), limit=1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["content"], "high")

    def test_change_risk_escalates_for_api_schema_and_low_coverage(self):
        result = predict_change_risk(["api.py", "schema.sql", "service.py"], fanout=20, coverage=0.4, api_change=True, schema_change=True, historical_defects=2)
        self.assertEqual(result["level"], "critical")
        self.assertIn("explicit_approval", result["controls"])

    def test_change_risk_is_low_for_small_well_covered_change(self):
        result = predict_change_risk(["README.md"], fanout=0, coverage=1.0)
        self.assertEqual(result["level"], "low")

    def test_eval_candidate_cannot_promote_on_required_regression(self):
        result = compare_eval_baseline({"accuracy": 0.95, "latency": 100}, {"accuracy": 0.94, "latency": 80})
        self.assertFalse(result["promotable"])
        self.assertIn("accuracy", result["regressions"])
        self.assertEqual(result["deltas"]["latency"], -20.0)

    def test_eval_candidate_can_promote_when_required_metrics_hold(self):
        result = compare_eval_baseline({"accuracy": 0.95}, {"accuracy": 0.96})
        self.assertTrue(result["promotable"])


if __name__ == '__main__':
    unittest.main()
