import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.world_model import Observation, WorldModel


class WorldModelPredictionTests(unittest.TestCase):
    def test_predict_next_learns_action_conditioned_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            world = WorldModel(memory, "project-x")
            world.observe(Observation("o1", "job", "state", "idle", "test", observed_at="2026-01-01T00:00:00+00:00"))
            world.observe(Observation("o2", "job", "state", "running", "test", observed_at="2026-01-01T00:01:00+00:00", properties={"action": "start"}))
            world.observe(Observation("o3", "job", "state", "idle", "test", observed_at="2026-01-01T00:02:00+00:00", properties={"action": "reset"}))
            world.observe(Observation("o4", "job", "state", "running", "test", observed_at="2026-01-01T00:03:00+00:00", properties={"action": "start"}))
            prediction = world.predict_next("job", "state", "start", current_value="idle")
            self.assertIsNotNone(prediction)
            self.assertEqual(prediction.predicted_value, "running")
            self.assertGreaterEqual(prediction.confidence, 1.0)
            scored = world.score_prediction(prediction, "running")
            self.assertTrue(scored.absolute_match)

    def test_predict_next_returns_none_without_learned_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = PersistentMemory(Path(directory) / "memory.db", require_approval=False)
            world = WorldModel(memory, "project-x")
            world.observe(Observation("o1", "job", "state", "idle", "test"))
            self.assertIsNone(world.predict_next("job", "state", "start"))


if __name__ == "__main__":
    unittest.main()
