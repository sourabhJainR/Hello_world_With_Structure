import unittest

from portable.task_planner import Task, TaskPlan


class TaskPlannerControlLoopTests(unittest.TestCase):
    def test_parallel_ready_is_dependency_safe_and_deterministic(self) -> None:
        plan = TaskPlan([
            Task("a", "A", parallel_group="g1", checkpoint="after-a", verification_strategy=["unit"]),
            Task("b", "B", parallel_group="g1", checkpoint="after-b", verification_strategy=["unit"]),
            Task("c", "C", dependencies=["a", "b"]),
        ])
        ready = plan.parallel_ready()
        self.assertEqual([task.id for task in ready], ["a", "b"])
        plan.tasks["a"].status = "done"
        self.assertEqual([task.id for task in plan.parallel_ready()], ["b"])

    def test_serialization_preserves_execution_metadata(self) -> None:
        task = Task("a", "A", parallel_group="g1", checkpoint="cp", verification_strategy=["lint", "unit"])
        restored = TaskPlan.from_dict(TaskPlan([task]).to_dict()).tasks["a"]
        self.assertEqual(restored.parallel_group, "g1")
        self.assertEqual(restored.checkpoint, "cp")
        self.assertEqual(restored.verification_strategy, ["lint", "unit"])


if __name__ == "__main__":
    unittest.main()
