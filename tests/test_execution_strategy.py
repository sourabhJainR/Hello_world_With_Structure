import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from portable.execution_strategy import PathwayOptimizer, execution_strategy, max_verification_depth
from portable.experience_router import ExperienceRouter


class ExecutionStrategyTests(unittest.TestCase):
    def test_unknown_strategy_is_safe_default(self):
        profile = execution_strategy("invented-pathway")
        self.assertFalse(profile.known)
        self.assertEqual(profile.name, "default")
        self.assertEqual(profile.verification_depth, "standard")

    def test_strategy_never_lowers_required_verification(self):
        self.assertEqual(max_verification_depth("standard", "deep"), "deep")
        self.assertEqual(max_verification_depth("independent", "standard"), "independent")

    def test_pathway_optimizer_discovers_bounded_alternative(self):
        with TemporaryDirectory() as directory:
            optimizer = PathwayOptimizer(ExperienceRouter(Path(directory), minimum_samples=2))
            pathway = optimizer.discover(
                capabilities=("delegate_task", "structured_output"),
                key_prefix="review:task",
                strategy=execution_strategy("evidence-first"),
                risk=0.3,
                evidence_quality=0.7,
                resource_lanes=("agent", "local"),
            )
            self.assertIn(pathway.capability, {"delegate_task", "structured_output"})
            self.assertIn(pathway.resource_lane, {"agent", "local"})
            self.assertEqual(pathway.verification_depth, "deep")
            self.assertGreaterEqual(pathway.score, 0.01)


if __name__ == "__main__":
    unittest.main()
