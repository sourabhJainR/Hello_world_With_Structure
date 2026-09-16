import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.reasoning_ledger import ReasoningLedger, ReasoningRecord


class ReasoningLedgerTests(unittest.TestCase):
    def test_round_trip_is_durable_and_digest_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            ledger = ReasoningLedger(memory, "demo")
            record = ReasoningRecord("r1", "run-1", "diagnose", ("o1",), ("h1", "h2"),
                                     ("retry", "inspect trace"), "inspect trace", "read logs", "found timeout",
                                     ("e1",), 0.7, "2026-01-01T00:00:00+00:00")
            ledger.append(record)
            ledger.append(record)
            reopened = ReasoningLedger(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            self.assertEqual(reopened.run("run-1"), (record,))
            self.assertEqual(reopened.digest("run-1"), ledger.digest("run-1"))

    def test_identity_collision_and_invalid_timestamp_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ReasoningLedger(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            record = ReasoningRecord("r1", "run-1", "observe", recorded_at="2026-01-01T00:00:00+00:00")
            ledger.append(record)
            with self.assertRaises(ValueError):
                ledger.append(ReasoningRecord("r1", "run-1", "act", recorded_at="2026-01-01T00:00:00+00:00"))
            with self.assertRaisesRegex(ValueError, "timezone"):
                ReasoningRecord("r2", "run-1", "observe", recorded_at="2026-01-01T00:00:00")

    def test_budget_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = ReasoningLedger(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo", max_records=1)
            ledger.append(ReasoningRecord("r1", "run-1", "observe"))
            with self.assertRaisesRegex(ValueError, "budget exceeded"):
                ledger.append(ReasoningRecord("r2", "run-1", "observe"))


if __name__ == "__main__":
    unittest.main()
