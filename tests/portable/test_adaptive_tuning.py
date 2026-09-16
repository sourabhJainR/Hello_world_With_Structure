import tempfile
import unittest
from pathlib import Path

from portable.adaptive_learning import AdaptiveLearningStore
from portable.adaptive_tuning import AdaptiveTuner
from portable.persistent_memory import PersistentMemory


class AdaptiveTuningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.memory = PersistentMemory(Path(self.directory.name) / "memory.db", require_approval=False)
        self.store = AdaptiveLearningStore(self.memory, "project-x")
        self.tuner = AdaptiveTuner(self.memory, "project-x")

    def tearDown(self):
        self.directory.cleanup()

    def _record(self, task_id, *, strategy="default", quality=1.0, iterations=2, confidence=0.7,
                evaluation_class="experience", capability="planning"):
        return self.tuner.record_experience(
            task_id=task_id,
            capability=capability,
            strategy=strategy,
            quality=quality,
            iterations=iterations,
            confidence=confidence,
            verified=True,
            evidence=(f"e-{task_id}",),
            evaluation_class=evaluation_class,
        )

    def test_experience_history_is_append_only(self):
        first = self._record("t1")
        second = self._record("t2")
        history = self.tuner.history()
        self.assertEqual([item.record_id for item in history], [first.record_id, second.record_id])

    def test_insufficient_history_does_not_change_policy(self):
        self._record("t1", strategy="candidate", quality=1.0, iterations=1)
        decision = self.tuner.evaluate("planning", candidate_strategy="candidate")
        self.assertEqual(decision.action, "hold")
        self.assertEqual(self.tuner.current_policy("planning").strategy, "default")

    def test_repeated_independent_strategy_gain_promotes(self):
        for i in range(6):
            self._record(f"base-{i}", strategy="default", quality=0.85, iterations=3)
            self._record(f"cand-{i}", strategy="fast", quality=0.95, iterations=2)
        for i in range(2):
            self._record(f"hold-{i}", strategy="fast", quality=0.95, iterations=2, evaluation_class="holdout")
        decision = self.tuner.evaluate("planning", candidate_strategy="fast")
        self.assertEqual(decision.action, "promote")
        self.assertEqual(self.tuner.current_policy("planning").strategy, "fast")

    def test_overconfidence_is_calibrated_without_certainty(self):
        for i, realized in enumerate((False, False, True, False, True, False, False, True)):
            self.tuner.record_experience(
                task_id=f"c-{i}", capability="planning", strategy="default", quality=1.0 if realized else 0.0,
                iterations=2, confidence=0.9, verified=True, evidence=(f"e-{i}",),
                evaluation_class="experience", realized_success=realized,
            )
        decision = self.tuner.evaluate("planning")
        self.assertLess(decision.confidence_adjustment, 0)
        self.assertLess(abs(decision.confidence_adjustment), 0.2)

    def test_iteration_target_reduces_only_with_holdout_evidence(self):
        for i in range(8):
            self._record(f"r-{i}", quality=0.95, iterations=1, evaluation_class="adaptation")
            self._record(f"h-{i}", quality=0.95, iterations=1, evaluation_class="holdout")
        decision = self.tuner.evaluate("planning")
        self.assertLess(decision.iteration_target, decision.previous_iteration_target)

    def test_quality_regression_blocks_iteration_reduction(self):
        for i in range(8):
            self._record(f"r-{i}", quality=0.95, iterations=1, evaluation_class="adaptation")
            self._record(f"h-{i}", quality=0.70, iterations=1, evaluation_class="holdout")
        decision = self.tuner.evaluate("planning")
        self.assertGreaterEqual(decision.iteration_target, decision.previous_iteration_target)


if __name__ == "__main__":
    unittest.main()
