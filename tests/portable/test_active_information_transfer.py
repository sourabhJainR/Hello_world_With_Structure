import tempfile
import unittest
from pathlib import Path

from portable.active_information import ActiveInformationLoop, InformationExecution
from portable.information_planner import InformationAction
from portable.learning_transfer import LearningExperience, LearningTransfer
from portable.persistent_memory import PersistentMemory
from portable.transfer_validation import TransferValidation, TransferValidator


class ActiveInformationTests(unittest.TestCase):
    def test_executes_selected_probe_and_measures_realized_gain(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            loop = ActiveInformationLoop(memory, "project-x")
            actions = (InformationAction("inspect", "inspect parser", 0.8, cost=2.0, risk=0.1),)
            result = loop.execute(
                uncertainty=0.9,
                actions=actions,
                probe=lambda action: InformationExecution(
                    uncertainty_after=0.2,
                    evidence_ids=("ev1",),
                    detail=f"ran {action.action_id}",
                ),
            )
            self.assertEqual(result.action_id, "inspect")
            self.assertAlmostEqual(result.realized_gain, 0.7)
            self.assertEqual(result.evidence_ids, ("ev1",))
            self.assertTrue(result.verified)
            memory.close()

    def test_rejected_probe_is_never_executed(self):
        called = False
        def probe(_action):
            nonlocal called
            called = True
            return InformationExecution(0.1)
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            loop = ActiveInformationLoop(memory, "project-x")
            with self.assertRaises(ValueError):
                loop.execute(
                    uncertainty=0.7,
                    actions=(InformationAction("risky", "risky", 0.8, cost=2.0, risk=0.9),),
                    max_risk=0.2,
                    probe=probe,
                )
            self.assertFalse(called)
            memory.close()

    def test_probe_failures_are_bounded_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            loop = ActiveInformationLoop(memory, "project-x")
            result = loop.execute(
                uncertainty=0.7,
                actions=(InformationAction("inspect", "inspect", 0.5),),
                probe=lambda _action: (_ for _ in ()).throw(RuntimeError("probe failed")),
            )
            self.assertFalse(result.verified)
            self.assertEqual(result.realized_gain, 0.0)
            self.assertIn("probe failed", result.error or "")
            memory.close()


class TransferValidationTests(unittest.TestCase):
    def _candidate(self, memory):
        transfer = LearningTransfer(memory, "target")
        transfer.record(LearningExperience(
            "e1", "source-a", "parser", "debug", "worked", "use targeted trace",
            ("src-e1",), 0.9, True, ("trace", "parser"), (),
        ))
        return transfer, transfer.transfer_structural("parser", "debug", ("trace", "parser"), min_similarity=0.5)[0]

    def test_failed_validation_is_recorded_and_blocks_repeat_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            transfer, candidate = self._candidate(memory)
            validator = TransferValidator(transfer)
            validation = validator.validate(candidate, lambda: TransferValidation(False, ("target-f1",), "introduced regression"))
            self.assertFalse(validation.success)
            self.assertTrue(validation.negative_transfer)
            self.assertEqual(transfer.transfer_structural("parser", "debug", ("trace", "parser"), min_similarity=0.5), [])
            memory.close()

    def test_successful_validation_requires_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            transfer, candidate = self._candidate(memory)
            validator = TransferValidator(transfer)
            result = validator.validate(candidate, lambda: TransferValidation(True, (), "no evidence"))
            self.assertFalse(result.success)
            self.assertTrue(result.reasons)
            memory.close()

    def test_successful_validation_is_recorded_as_target_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            transfer, candidate = self._candidate(memory)
            validator = TransferValidator(transfer)
            result = validator.validate(candidate, lambda: TransferValidation(True, ("target-e1",), "worked"))
            self.assertTrue(result.success)
            self.assertFalse(result.negative_transfer)
            memory.close()


if __name__ == "__main__":
    unittest.main()
