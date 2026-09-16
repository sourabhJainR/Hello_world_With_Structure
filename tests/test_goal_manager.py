import tempfile
import unittest
from pathlib import Path

from portable.goal_manager import Goal, GoalManager
from portable.persistent_memory import PersistentMemory


class GoalManagerTests(unittest.TestCase):
    def test_hierarchy_is_durable_and_ready_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.db"
            manager = GoalManager(PersistentMemory(path, require_approval=False), "demo")
            root = manager.create(Goal("g1", "Improve reliability", priority=80, created_at="2026-01-01T00:00:00+00:00"))
            child = manager.create(Goal("g2", "Investigate timeout", parent_id=root.goal_id, priority=90, created_at="2026-01-01T01:00:00+00:00"))
            self.assertEqual(manager.children("g1")[0], child)
            self.assertEqual(manager.ready()[0].goal_id, "g2")
            reopened = GoalManager(PersistentMemory(path, require_approval=False), "demo")
            self.assertEqual(reopened.get("g1"), root)

    def test_terminal_goals_cannot_be_reopened_and_missing_parent_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = GoalManager(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            with self.assertRaises(KeyError):
                manager.create(Goal("g1", "child", parent_id="missing"))
            manager.create(Goal("g1", "root"))
            manager.set_status("g1", "completed")
            with self.assertRaisesRegex(ValueError, "terminal"):
                manager.set_status("g1", "active")

    def test_validation_is_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            Goal("g1", "self", parent_id="g1")
        with self.assertRaises(ValueError):
            Goal("g1", "bad", priority=101)
        with self.assertRaisesRegex(ValueError, "timezone"):
            Goal("g1", "bad", created_at="2026-01-01T00:00:00")


if __name__ == "__main__":
    unittest.main()
