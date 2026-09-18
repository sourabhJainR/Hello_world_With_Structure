import tempfile
import unittest
from pathlib import Path

from portable.aer_console import collect_snapshot
from portable.adaptive_tuning import AdaptiveTuner
from portable.persistent_memory import PersistentMemory


class LearningTransparencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / ".aer"
        memory = PersistentMemory(self.home / "memory" / "memory.db")
        project = "project-alpha"
        self.tuner = AdaptiveTuner(memory, project)
        for index in range(4):
            self.tuner.record_experience(
                task_id=f"task-{index}",
                capability="implementation",
                strategy="single-agent",
                quality=0.95,
                iterations=2,
                confidence=0.9,
                verified=True,
                evidence=(f"ev-{index}",),
            )
        self.tuner.record_maintenance_receipt(
            started_at="2026-09-18T00:00:00+00:00",
            jobs_processed=4,
            strategy_action="hold",
            policy_version="v1",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_exposes_advisory_learning_state(self):
        snapshot = collect_snapshot(self.home)
        learning = snapshot.learning
        self.assertEqual(learning["adaptive"]["status"], "active")
        self.assertTrue(learning["adaptive"]["advisory_only"])
        self.assertEqual(learning["adaptive"]["experience_count"], 4)
        self.assertEqual(learning["adaptive"]["policies"][0]["version"], "v1")
        self.assertEqual(learning["adaptive"]["maintenance"][0]["jobs_processed"], 4)

    def test_learning_diagnostics_do_not_mutate_policy(self):
        before = self.tuner.current_policy("global")
        collect_snapshot(self.home)
        after = self.tuner.current_policy("global")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
