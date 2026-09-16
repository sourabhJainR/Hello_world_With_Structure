from pathlib import Path
import unittest

from portable.persistent_memory import PersistentMemory
from portable.world_model import Observation, WorldModel


class WorldModelTests(unittest.TestCase):
    def test_observations_are_durable_and_current_state_is_latest(self) -> None:
        root = Path(self.id().replace(".", "_"))
        root.mkdir(exist_ok=True)
        try:
            memory = PersistentMemory(root / "memory.db", require_approval=False)
            model = WorldModel(memory, "demo")
            model.observe(Observation("o1", "service", "status", "degraded", "monitor", observed_at="2026-01-01T00:00:00+00:00", evidence=("metric-1",)))
            model.observe(Observation("o2", "service", "status", "healthy", "monitor", observed_at="2026-01-02T00:00:00+00:00", confidence=0.9))
            model.observe(Observation("o3", "service", "version", "2.0", "deploy", observed_at="2026-01-02T01:00:00+00:00"))

            self.assertEqual(model.current("service", "status")[0].value, "healthy")
            self.assertEqual(model.current("service", "status")[0].observation_id, "o2")
            self.assertEqual(model.current("service")[0].predicate, "status")
            self.assertEqual(len(model.history("service", "status")), 2)

            reopened = WorldModel(PersistentMemory(root / "memory.db", require_approval=False), "demo")
            self.assertEqual(reopened.current("service", "version")[0].value, "2.0")
            self.assertEqual(reopened.digest(), model.digest())
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_observation_identity_is_idempotent_but_collision_is_rejected(self) -> None:
        root = Path(self.id().replace(".", "_"))
        root.mkdir(exist_ok=True)
        try:
            model = WorldModel(PersistentMemory(root / "memory.db", require_approval=False), "demo")
            observation = Observation("same", "x", "state", {"ok": True}, "test", observed_at="2026-01-01T00:00:00+00:00")
            model.observe(observation)
            model.observe(observation)
            with self.assertRaisesRegex(ValueError, "different content"):
                model.observe(Observation("same", "x", "state", {"ok": False}, "test", observed_at="2026-01-01T00:00:00+00:00"))
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)

    def test_bounds_and_validation(self) -> None:
        root = Path(self.id().replace(".", "_"))
        root.mkdir(exist_ok=True)
        try:
            model = WorldModel(PersistentMemory(root / "memory.db", require_approval=False), "demo", max_observations=1)
            model.observe(Observation("o1", "x", "state", True, "test"))
            with self.assertRaisesRegex(ValueError, "budget exceeded"):
                model.observe(Observation("o2", "x", "state", False, "test"))
            with self.assertRaises(ValueError):
                Observation("o3", "x", "state", True, "test", confidence=1.1)
            with self.assertRaisesRegex(ValueError, "timezone"):
                Observation("o4", "x", "state", True, "test", observed_at="2026-01-03T00:00:00")
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
