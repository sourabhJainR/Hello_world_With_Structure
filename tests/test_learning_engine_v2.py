import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".ai-harness" / "runtime"))

from canary_evaluator import evaluate_staged_canary
from experience_store import Experience, ExperienceStore
from learning_engine import Observation, learn, score_candidates
from regression_replay import ReplayCase
from regression_selector import select_regressions


class LearningEngineV2Tests(unittest.TestCase):
    def test_experience_store_is_durable_and_queryable_by_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "experience.db"
            store = ExperienceStore(path)
            store.record(Experience("1", "bug", "targeted", True, True, True))
            store.record(Experience("2", "feature", "broad", True, True, True))
            reopened = ExperienceStore(path)
            rows = reopened.by_task_class("bug")
            self.assertEqual([r.task_id for r in rows], ["1"])
            self.assertEqual(reopened.count(), 2)

    def test_sparse_strategy_is_not_eligible_under_confidence_gate(self):
        rows = [Observation(str(i), "bug", "lucky", True, True, True) for i in range(3)]
        scores = score_candidates(rows, min_samples=3, min_lower_bound=.70)
        self.assertFalse(scores[0].eligible)
        self.assertIn("confidence lower bound below gate", scores[0].reasons)

    def test_candidate_uses_history_not_only_current_observation(self):
        rows = [Observation(str(i), "bug", "stable", True, True, True, timestamp=i) for i in range(10)]
        candidates = learn(rows, min_samples=5, min_lower_bound=.70)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].sample_count, 10)
        self.assertEqual(len(candidates[0].evidence), 10)

    def test_regression_selector_prioritizes_family_and_known_failures(self):
        cases = [ReplayCase("bug-fail", "bug", True), ReplayCase("bug-ok", "bug", True), ReplayCase("feature", "feature", True)]
        selection = select_regressions(cases, task_class="bug", limit=2, historical_failures=["bug-fail"])
        self.assertEqual(selection.case_ids[0], "bug-fail")
        self.assertEqual(selection.coverage["same_family"], 2)

    def test_canary_halts_on_first_failed_stage(self):
        candidate = learn([Observation(str(i), "bug", "stable", True, True, True) for i in range(10)], min_samples=5, min_lower_bound=.70)[0]
        cases = [ReplayCase(f"r{i}", "bug", True) for i in range(5)]
        calls = []
        def runner(case, _candidate):
            calls.append(case.case_id)
            return (case.case_id != "r0", True)
        plan = evaluate_staged_canary(candidate, cases, runner, min_cases_per_stage=2)
        self.assertFalse(plan.promoted)
        self.assertEqual(plan.halted_at, 1)
        self.assertEqual(len(plan.stages), 1)

    def test_canary_reaches_full_promotion_plan_when_all_stages_pass(self):
        candidate = learn([Observation(str(i), "bug", "stable", True, True, True) for i in range(10)], min_samples=5, min_lower_bound=.70)[0]
        cases = [ReplayCase(f"r{i}", "bug", True) for i in range(10)]
        plan = evaluate_staged_canary(candidate, cases, lambda _case, _candidate: (True, True), min_cases_per_stage=2)
        self.assertTrue(plan.promoted)
        self.assertEqual(len(plan.stages), 5)
        self.assertIsNone(plan.halted_at)


if __name__ == "__main__":
    unittest.main()
