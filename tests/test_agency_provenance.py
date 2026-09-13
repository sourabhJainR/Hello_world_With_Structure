import tempfile
import unittest
from pathlib import Path

from portable.agency_provenance import ProvenanceLedger


class ProvenanceLedgerTests(unittest.TestCase):
    def test_chain_round_trip(self):
        ledger = ProvenanceLedger()
        first = ledger.append("run-1", "started", "task accepted")
        second = ledger.append("run-1", "artifact-verified", artifact_ids=["a2", "a1"])
        self.assertEqual(second.parent_hash, first.record_hash)
        restored = ProvenanceLedger.from_jsonl(ledger.to_jsonl())
        self.assertEqual([r.record_hash for r in restored.records], [r.record_hash for r in ledger.records])

    def test_tampering_is_rejected(self):
        ledger = ProvenanceLedger()
        ledger.append("run-1", "started")
        text = ledger.to_jsonl().replace('"detail": ""', '"detail": "tampered"')
        with self.assertRaises(ValueError):
            ProvenanceLedger.from_jsonl(text)

    def test_schema_tampering_is_rejected(self):
        ledger = ProvenanceLedger()
        ledger.append("run-1", "started")
        text = ledger.to_jsonl().replace('"artifact_ids": []', '"artifact_ids": {}')
        with self.assertRaises(ValueError):
            ProvenanceLedger.from_jsonl(text)

    def test_file_round_trip(self):
        ledger = ProvenanceLedger()
        ledger.append("run-1", "completed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger.write(path)
            loaded = ProvenanceLedger.read(path)
        self.assertEqual(loaded.records[0].event, "completed")


if __name__ == "__main__":
    unittest.main()
