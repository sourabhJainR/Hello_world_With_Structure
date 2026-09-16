import unittest

from portable.execution_contract import ExecutionEnvelope, ExecutionIntent, ExecutionPlanRef, RepositoryReference


class ExecutionControlLoopTests(unittest.TestCase):
    def test_iteration_and_wake_metadata_round_trip(self) -> None:
        envelope = ExecutionEnvelope(
            ExecutionIntent("task-1", "improve runtime"),
            RepositoryReference("repo-1"),
            ExecutionPlanRef("plan-1", ("task-1",)),
            iteration=3,
            wake_reason="regression-detected",
            prior_outcome_id="outcome-2",
            next_action_ids=("action-1", "action-2"),
        )
        restored = ExecutionEnvelope.from_dict(envelope.to_dict())
        self.assertEqual(restored.iteration, 3)
        self.assertEqual(restored.wake_reason, "regression-detected")
        self.assertEqual(restored.prior_outcome_id, "outcome-2")
        self.assertEqual(restored.next_action_ids, ("action-1", "action-2"))
        self.assertEqual(restored.digest, envelope.digest)

    def test_negative_iteration_is_rejected(self) -> None:
        envelope = ExecutionEnvelope(
            ExecutionIntent("task-1", "improve runtime"),
            RepositoryReference("repo-1"),
            ExecutionPlanRef("plan-1", ("task-1",)),
            iteration=-1,
        )
        with self.assertRaises(ValueError):
            envelope.validate()


if __name__ == "__main__":
    unittest.main()
