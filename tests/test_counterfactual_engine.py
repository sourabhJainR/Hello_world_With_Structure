from __future__ import annotations

import unittest

from portable.counterfactual_engine import BranchCandidate, CounterfactualEngine


class CounterfactualEngineTests(unittest.TestCase):
    def test_counterfactual_selection_is_deterministic_and_auditable(self) -> None:
        engine = CounterfactualEngine(min_confidence=0.5, min_margin=0.01)
        state = {"task": "repair", "risk": "normal"}
        branches = [
            BranchCandidate("deep-verify", 0.92, 0.95, 0.35, 0.10, 0.90, 0.40, 0.0, "more independent evidence"),
            BranchCandidate("fast-verify", 0.80, 0.70, 0.20, 0.20, 0.75, 0.20),
        ]
        decision = engine.evaluate(state, branches)
        self.assertEqual(decision.selected, "deep-verify")
        self.assertFalse(decision.abstained)
        self.assertTrue(decision.state_digest)
        self.assertEqual(decision.branches[0].name, "deep-verify")
        self.assertGreater(decision.branches[0].utility, decision.branches[1].utility)
        self.assertEqual(decision.as_dict()["selected"], "deep-verify")

    def test_low_confidence_abstains_instead_of_forcing_a_branch(self) -> None:
        engine = CounterfactualEngine(min_confidence=0.90, min_margin=0.01)
        decision = engine.evaluate(
            {"task": "uncertain"},
            [
                BranchCandidate("a", 0.70, 0.70, confidence=0.60),
                BranchCandidate("b", 0.68, 0.70, confidence=0.60),
            ],
        )
        self.assertTrue(decision.abstained)
        self.assertIsNone(decision.selected)
        self.assertIsNone(engine.as_choice(decision))

    def test_close_alternatives_trigger_margin_abstention(self) -> None:
        engine = CounterfactualEngine(min_confidence=0.5, min_margin=0.5)
        decision = engine.evaluate(
            {},
            [
                BranchCandidate("a", 0.90, 0.80, cost=0.2, confidence=0.9),
                BranchCandidate("b", 0.89, 0.80, cost=0.2, confidence=0.9),
            ],
        )
        self.assertTrue(decision.abstained)
        self.assertIsNone(decision.selected)
        self.assertIn("insufficient", decision.reason)

    def test_duplicate_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            CounterfactualEngine().evaluate(
                {},
                [
                    BranchCandidate("same", 0.8, 0.8),
                    BranchCandidate("same", 0.7, 0.8),
                ],
            )

    def test_ties_are_resolved_by_stable_name_order(self) -> None:
        engine = CounterfactualEngine(min_confidence=0.0, min_margin=0.0)
        decision = engine.evaluate(
            {},
            [
                BranchCandidate("z", 0.8, 0.8, cost=0.2, confidence=1.0),
                BranchCandidate("a", 0.8, 0.8, cost=0.2, confidence=1.0),
            ],
        )
        self.assertEqual(decision.selected, "a")


if __name__ == "__main__":
    unittest.main()
