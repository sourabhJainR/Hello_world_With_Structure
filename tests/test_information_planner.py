import unittest

from portable.information_planner import InformationAction, InformationPlanner


class InformationPlannerTests(unittest.TestCase):
    def test_chooses_best_information_value(self) -> None:
        planner = InformationPlanner()
        actions = (
            InformationAction("slow", "run expensive test", 0.8, cost=4),
            InformationAction("fast", "inspect trace", 0.5, cost=1),
            InformationAction("risky", "production experiment", 0.9, cost=1, risk=0.8),
        )
        plan = planner.choose(uncertainty=0.7, actions=actions, max_risk=0.5)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.action_id, "fast")
        self.assertAlmostEqual(plan.expected_uncertainty_after, 0.2)

    def test_risk_and_empty_actions_fail_closed(self) -> None:
        planner = InformationPlanner()
        self.assertIsNone(planner.choose(uncertainty=0.5, actions=(InformationAction("r", "risky", 1, risk=0.9),), max_risk=0.5))
        self.assertIsNone(planner.choose(uncertainty=0.5, actions=()))
        with self.assertRaises(ValueError):
            planner.choose(uncertainty=1.1, actions=())
        with self.assertRaises(ValueError):
            InformationAction("x", "bad", 1, cost=0)


if __name__ == "__main__":
    unittest.main()
