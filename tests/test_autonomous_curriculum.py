import unittest
from pathlib import Path

from portable.autonomous_curriculum import AutonomousCurriculumDiscovery
from portable.persistent_memory import PersistentMemory


class AutonomousCurriculumTests(unittest.TestCase):
    def make_discovery(self):
        path = Path(self._testMethodName + ".sqlite3")
        if path.exists():
            path.unlink()
        memory = PersistentMemory(path, require_approval=False)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return AutonomousCurriculumDiscovery(memory, "demo")

    def test_selection_is_deterministic_and_budgeted(self):
        discovery = self.make_discovery()
        first = discovery.discover(
            "planner", ["search", "reasoning", "verification"],
            uncertainty={"search": 0.9, "reasoning": 0.4, "verification": 0.7}, budget=3)
        second = discovery.discover(
            "planner", ["search", "reasoning", "verification"],
            uncertainty={"search": 0.9, "reasoning": 0.4, "verification": 0.7}, budget=3)
        self.assertEqual(
            [(x.task_family, x.condition) for x in first.selected],
            [(x.task_family, x.condition) for x in second.selected],
        )
        self.assertEqual(len(first.selected), 3)
        self.assertEqual({x.task_family for x in first.selected},
                         {"search", "reasoning", "verification"})

    def test_unresolved_failures_raise_priority(self):
        discovery = self.make_discovery()
        before = discovery.discover(
            "planner", ["search", "verification"],
            uncertainty={"search": 0.5, "verification": 0.5}, budget=2)
        target = before.selected[0]
        discovery.record_outcome("planner", target.task_family, target.condition, score=0.2)
        after = discovery.discover(
            "planner", ["search", "verification"],
            uncertainty={"search": 0.5, "verification": 0.5}, budget=2)
        chosen = next(x for x in after.candidates
                      if (x.task_family, x.condition) == (target.task_family, target.condition))
        self.assertGreater(chosen.failure_rate, 0)
        self.assertGreater(chosen.priority, 0)

    def test_verified_success_reduces_repeated_probe_priority(self):
        discovery = self.make_discovery()
        before = discovery.discover(
            "planner", ["search", "verification"],
            uncertainty={"search": 0.8, "verification": 0.8}, budget=2)
        target = before.selected[0]
        for _ in range(3):
            discovery.record_outcome(
                "planner", target.task_family, target.condition, score=0.98)
        after = discovery.discover(
            "planner", ["search", "verification"],
            uncertainty={"search": 0.8, "verification": 0.8}, budget=2)
        chosen = next(x for x in after.candidates
                      if (x.task_family, x.condition) == (target.task_family, target.condition))
        self.assertEqual(chosen.historical_count, 3)
        self.assertLess(chosen.expected_information_gain, target.expected_information_gain)

    def test_invalid_inputs_are_rejected(self):
        discovery = self.make_discovery()
        with self.assertRaises(ValueError):
            discovery.discover("planner", ["search"], budget=2)
        with self.assertRaises(ValueError):
            discovery.discover(
                "planner", ["search", "verification"],
                uncertainty={"search": 1.5}, budget=2)


if __name__ == "__main__":
    unittest.main()
