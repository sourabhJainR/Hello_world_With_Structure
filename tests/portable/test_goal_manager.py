import tempfile
import unittest
from pathlib import Path

from portable.goal_manager import Goal, GoalManager
from portable.persistent_memory import PersistentMemory


class GoalManagerTests(unittest.TestCase):
    def test_goal_dependencies_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = GoalManager(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")
            manager.create(Goal("g1", "Build base", priority=50))
            manager.create(Goal("g2", "Build feature", priority=90, dependencies=("g1",), progress=0.25))
            self.assertEqual(manager.ready(), (manager.get("g1"),))
            manager.set_status("g1", "completed")
            self.assertEqual(manager.ready()[0].goal_id, "g2")
            manager.set_progress("g2", 1.0)
            self.assertEqual(manager.get("g2").progress, 1.0)

    def test_expired_incomplete_goal_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = GoalManager(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")
            manager.create(Goal("g1", "Late goal", deadline_at="2026-01-01T00:00:00+00:00"))
            self.assertEqual(manager.ready(now="2026-02-01T00:00:00+00:00"), ())

    def test_unknown_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = GoalManager(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "project-x")
            with self.assertRaises(KeyError):
                manager.create(Goal("g1", "Feature", dependencies=("missing",)))


if __name__ == "__main__":
    unittest.main()
