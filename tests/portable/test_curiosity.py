import unittest

from portable.curiosity import CuriosityEngine, LearningNeed


class CuriosityTests(unittest.TestCase):
    def test_curiosity_prioritizes_high_value_uncertainty(self):
        engine = CuriosityEngine()
        choices = engine.rank([
            LearningNeed("parser", 0.8, 0.9, 1.0, 0.1, 0.1),
            LearningNeed("formatting", 0.5, 0.2, 0.5, 0.5, 0.1),
        ])
        self.assertEqual(choices[0].capability, "parser")

    def test_curiosity_respects_risk_and_budget(self):
        engine = CuriosityEngine()
        choice = engine.choose([
            LearningNeed("unsafe", 1.0, 1.0, 0.9, 0.1, 1.0),
            LearningNeed("safe", 0.7, 0.8, 1.0, 0.5, 0.1),
        ], max_cost=1.0, max_risk=0.5)
        self.assertIsNotNone(choice)
        self.assertEqual(choice.capability, "safe")

    def test_curiosity_is_deterministic_for_ties(self):
        engine = CuriosityEngine()
        choices = engine.rank([
            LearningNeed("b", 1.0, 1.0, 1.0, 1.0, 0.0),
            LearningNeed("a", 1.0, 1.0, 1.0, 1.0, 0.0),
        ])
        self.assertEqual([choice.capability for choice in choices], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
