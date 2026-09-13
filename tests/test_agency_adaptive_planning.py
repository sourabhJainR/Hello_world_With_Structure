import unittest

from portable.agency_adaptive_planning import (
    BenchmarkHistory,
    BenchmarkObservation,
    apply_recommendation,
    observe_run,
    provenance_head,
    recommend_plan,
)
from portable.agency_execution_plan import ExecutionPlan, ExecutionWave, PlanConflict
from portable.agency_provenance import ProvenanceLedger


class AgencyAdaptivePlanningTests(unittest.TestCase):
    def _passed(self, index, *, score=98, conflicts=0, waves=1, regression="passed"):
        return BenchmarkObservation(
            task_id=f"run-{index}",
            plan_digest=f"digest-{index}",
            provenance_head=f"head-{index}",
            release_status="passed",
            regression_status=regression,
            quality_score=score,
            wave_count=waves,
            conflict_count=conflicts,
            blocked_count=0,
        )

    def test_insufficient_history_keeps_requested_posture(self):
        rec = recommend_plan([], requested_mutation_mode="bounded", requested_support_limit=2)
        self.assertEqual(rec.mutation_mode, "bounded")
        self.assertEqual(rec.support_limit, 2)
        self.assertEqual(rec.confidence, "none")

    def test_regression_feedback_tightens_mutation_mode(self):
        history = BenchmarkHistory([self._passed(i, regression="failed") for i in range(3)])
        rec = recommend_plan(history, requested_mutation_mode="bounded", requested_support_limit=2)
        self.assertEqual(rec.mutation_mode, "read-only")
        self.assertTrue(any("regressions" in reason for reason in rec.reasons))

    def test_high_quality_low_conflict_history_allows_extra_support(self):
        history = BenchmarkHistory([self._passed(i) for i in range(4)])
        rec = recommend_plan(history, requested_mutation_mode="bounded", requested_support_limit=2)
        self.assertEqual(rec.support_limit, 3)
        self.assertEqual(rec.confidence, "high")

    def test_conflict_history_caps_support(self):
        history = BenchmarkHistory([self._passed(i, score=92, conflicts=1, waves=2) for i in range(4)])
        rec = recommend_plan(history, requested_mutation_mode="bounded", requested_support_limit=3)
        self.assertEqual(rec.support_limit, 1)
        self.assertTrue(any("conflicts" in reason for reason in rec.reasons))

    def test_apply_recommendation_never_exceeds_requested_support(self):
        history = BenchmarkHistory([self._passed(i) for i in range(4)])
        rec = recommend_plan(history, requested_mutation_mode="bounded", requested_support_limit=2)
        mode, support = apply_recommendation("bounded", 2, rec, allowed_mutation_modes={"bounded"})
        self.assertEqual(mode, "bounded")
        self.assertEqual(support, 2)

    def test_observation_binds_plan_and_provenance(self):
        ledger = ProvenanceLedger()
        ledger.append("run-1", "release-decision", "passed")
        plan = ExecutionPlan((ExecutionWave(0, ("builder",), True),), ())
        result = observe_run(
            task_id="run-1",
            plan=plan,
            provenance=ledger,
            release_status="passed",
            regression_status=None,
            quality_score=95,
            specialist_results=("builder:primary",),
        )
        self.assertEqual(result.plan_digest, plan.digest())
        self.assertEqual(result.provenance_head, provenance_head(ledger))
        self.assertEqual(result.regression_status, "omitted")
        self.assertEqual(result.wave_count, 1)
        self.assertEqual(result.specialist_results, ("builder:primary",))

    def test_jsonl_history_round_trip(self):
        history = BenchmarkHistory([self._passed(1), self._passed(2, conflicts=1)])
        restored = BenchmarkHistory.from_jsonl(history.to_jsonl())
        self.assertEqual([x.as_dict() for x in restored.observations], [x.as_dict() for x in history.observations])


if __name__ == "__main__":
    unittest.main()
