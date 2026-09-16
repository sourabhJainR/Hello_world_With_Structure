from __future__ import annotations
import unittest
from portable.agency_adaptive_planning import BenchmarkHistory, BenchmarkObservation, recommend_plan

class AdaptivePlanningEvidenceTests(unittest.TestCase):
    def obs(self, mode, passed=True):
        return BenchmarkObservation('task', 'plan', 'prov', 'passed' if passed else 'failed', 'passed', 95 if passed else 60, 1, 0, 0, (), mode, 'code-change', 'model-a', 20, 100, 10, 0, 0, 0)

    def test_insufficient_history_does_not_promote(self):
        rec=recommend_plan(BenchmarkHistory([self.obs('single-agent')]), min_samples=3)
        self.assertEqual(rec.execution_mode, 'single-agent')
        self.assertEqual(rec.confidence, 'none')

    def test_comparative_evidence_can_promote_mode(self):
        history=BenchmarkHistory([self.obs('single-agent', False), self.obs('single-agent', False), self.obs('multi-agent', True), self.obs('multi-agent', True)])
        rec=recommend_plan(history, min_samples=3)
        self.assertEqual(rec.execution_mode, 'multi-agent')
        self.assertGreaterEqual(rec.comparable_sample_count, 1)

if __name__ == '__main__': unittest.main()
