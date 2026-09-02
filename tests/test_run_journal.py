import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".ai-harness"))

from runtime.run_journal import append_event, replay, verify_chain


class RunJournalTests(unittest.TestCase):
    def test_hash_chain_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            append_event(root, "run.start", {"workflow": "adaptive"})
            append_event(root, "phase.start", {"phase": "execute"})
            append_event(root, "provider.finish", {"phase": "execute", "exit_code": 0})
            append_event(root, "run.finish", {"status": "completed"})

            chain = verify_chain(root)
            self.assertTrue(chain["passed"], chain)
            projection = replay(root)
            self.assertEqual(projection["status"], "completed")
            self.assertEqual(projection["phases"]["execute"]["finishes"], 1)

    def test_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            append_event(root, "run.start", {})
            append_event(root, "run.finish", {"status": "completed"})
            journal = root / "execution.journal.jsonl"
            lines = journal.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1].replace('"status": "completed"', '"status": "failed"')
            journal.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(verify_chain(root)["passed"])


if __name__ == "__main__":
    unittest.main()
