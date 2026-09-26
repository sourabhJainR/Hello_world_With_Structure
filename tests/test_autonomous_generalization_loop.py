import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.world_mega_model import WorldMegaModel
from portable.generalization_curriculum import ExperimentResult


class AutonomousGeneralizationLoopTests(unittest.TestCase):
    def test_cycle_discovers_evaluates_and_learns(self):
        path = Path("autonomous-generalization-cycle.sqlite3")
        if path.exists():
            path.unlink()
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        model = WorldMegaModel(
            PersistentMemory(path, require_approval=False), "cycle-demo"
        )

        def evaluator(experiment):
            return ExperimentResult(experiment.id, 0.9, f"evidence-{experiment.id}", True)

        cycle = model.run_autonomous_generalization_cycle(
            "planner",
            ["search", "verification", "reasoning"],
            evaluator,
            baseline_score=0.8,
            uncertainty={"search": 0.9, "verification": 0.6, "reasoning": 0.7},
            budget=3,
        )

        self.assertEqual(len(cycle.experiments), 3)
        self.assertTrue(cycle.report.generalized)
        self.assertEqual(cycle.report.generalization_score, 0.9)
        second = model.discover_generalization_curriculum(
            "planner",
            ["search", "verification", "reasoning"],
            uncertainty={"search": 0.9, "verification": 0.6, "reasoning": 0.7},
            budget=3,
        )
        self.assertEqual(sum(x.historical_count for x in second.candidates), 3)


if __name__ == "__main__":
    unittest.main()
