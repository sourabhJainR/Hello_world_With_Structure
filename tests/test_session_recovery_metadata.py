import json
import tempfile
import unittest
from pathlib import Path

from portable.session_state import SessionCheckpoint, SessionStore


class SessionRecoveryMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_checkpoint_persists_resume_context(self):
        store = SessionStore(self.root / "sessions")
        checkpoint = SessionCheckpoint(
            session_id="s1",
            task_id="t1",
            project_key="p1",
            stage="verify",
            project_root="/workspace/service",
            intent="Fix authentication timeout",
        )
        path = store.save(checkpoint)
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(raw["project_root"], "/workspace/service")
        self.assertEqual(raw["intent"], "Fix authentication timeout")
        restored = store.load("s1")
        self.assertIsNotNone(restored)
        self.assertEqual(restored.project_root, "/workspace/service")
        self.assertEqual(restored.intent, "Fix authentication timeout")

    def test_legacy_checkpoint_without_resume_fields_still_loads(self):
        store = SessionStore(self.root / "sessions")
        payload = {
            "session_id": "legacy",
            "task_id": "t1",
            "project_key": "p1",
            "stage": "execute",
            "completed_batches": [],
            "remaining_batches": [],
            "active_provider": None,
            "attempt": 0,
            "last_error": None,
            "updated_at": 12345.0,
            "state_digest": "",
        }
        payload["state_digest"] = __import__("hashlib").sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        path = store.path("legacy")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        restored = store.load("legacy")
        self.assertIsNotNone(restored)
        self.assertIsNone(restored.project_root)
        self.assertIsNone(restored.intent)


if __name__ == "__main__":
    unittest.main()
