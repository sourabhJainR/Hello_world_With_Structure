import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.self_model import SelfModel


class SelfModelTests(unittest.TestCase):
    def test_profile_is_empirical_and_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.db"
            model = SelfModel(PersistentMemory(path, require_approval=False), "demo")
            model.record("o1", "python", success=True)
            model.record("o2", "python", success=True)
            model.record("o3", "python", success=False)
            profile = model.profile("python")
            self.assertEqual((profile.successes, profile.failures, profile.observations), (2, 1, 3))
            self.assertAlmostEqual(profile.confidence, 2 / 3, places=6)
            self.assertTrue(model.should_escalate("python", min_observations=3, min_confidence=0.8))
            reopened = SelfModel(PersistentMemory(path, require_approval=False), "demo")
            self.assertEqual(reopened.profile("python"), profile)

    def test_identity_collision_and_thresholds_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = SelfModel(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            model.record("o1", "python", success=True)
            model.record("o1", "python", success=True)
            with self.assertRaises(ValueError):
                model.record("o1", "python", success=False)
            with self.assertRaises(ValueError):
                model.should_escalate("python", min_observations=0)
            with self.assertRaises(ValueError):
                model.should_escalate("python", min_confidence=1.1)

    def test_invalid_identifiers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = SelfModel(PersistentMemory(Path(directory) / "memory.db", require_approval=False), "demo")
            with self.assertRaises(ValueError):
                model.record(123, "python", success=True)  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                model.profile(123)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
