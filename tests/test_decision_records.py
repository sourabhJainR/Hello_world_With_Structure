import unittest

from portable.evidence_contract import DecisionRecord, decisions_from_state


class DecisionRecordTests(unittest.TestCase):
    def test_probabilistic_decision_requires_model_and_valid_probability(self) -> None:
        decision = DecisionRecord("d1", "route", ("e1",), typed_output="multi", probability=0.8, model_id="local-model")
        decision.validate(("e1",))
        with self.assertRaises(ValueError):
            DecisionRecord("bad", "route", ("e1",), probability=1.1, model_id="m").validate(("e1",))
        with self.assertRaises(ValueError):
            DecisionRecord("bad-model", "route", ("e1",), probability=0.8).validate(("e1",))

    def test_abstention_is_not_observed_truth(self) -> None:
        with self.assertRaises(ValueError):
            DecisionRecord("d1", "route", ("e1",), abstained=True, observed_outcome=True).validate(("e1",))

    def test_state_conversion_rejects_missing_evidence(self) -> None:
        with self.assertRaises(ValueError):
            decisions_from_state(
                [{"id": "d1", "decision": "route", "evidence_ids": ["missing"]}],
                evidence_ids=["e1"],
            )


if __name__ == "__main__":
    unittest.main()
