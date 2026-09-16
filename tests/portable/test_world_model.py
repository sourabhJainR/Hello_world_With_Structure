import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.world_model import Observation, WorldModel, WorldPrediction


class WorldModelPredictionTests(unittest.TestCase):
    def _world(self, directory: str, project: str = "project-x"):
        memory = PersistentMemory(Path(directory) / f"{project}.db", require_approval=False)
        return WorldModel(memory, project)

    def test_predict_next_learns_action_conditioned_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            world = self._world(directory)
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

    def test_prediction_confidence_accounts_for_competing_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            world = self._world(directory)
            world.observe(Observation("o1", "job", "state", "idle", "test", observed_at="2026-01-01T00:00:00+00:00"))
            world.observe(Observation("o2", "job", "state", "running", "test", observed_at="2026-01-01T00:01:00+00:00", properties={"action": "start"}))
            world.observe(Observation("o3", "job", "state", "idle", "test", observed_at="2026-01-01T00:02:00+00:00", properties={"action": "reset"}))
            world.observe(Observation("o4", "job", "state", "failed", "test", observed_at="2026-01-01T00:03:00+00:00", properties={"action": "start"}))
            world.observe(Observation("o5", "job", "state", "idle", "test", observed_at="2026-01-01T00:04:00+00:00", properties={"action": "reset"}))
            world.observe(Observation("o6", "job", "state", "running", "test", observed_at="2026-01-01T00:05:00+00:00", properties={"action": "start"}))
            prediction = world.predict_next("job", "state", "start", current_value="idle")
            self.assertIsNotNone(prediction)
            self.assertEqual(prediction.predicted_value, "running")
            self.assertAlmostEqual(prediction.confidence, 2 / 3)

    def test_score_rejects_prediction_from_other_project(self):
        with tempfile.TemporaryDirectory() as directory:
            world_x = self._world(directory, "project-x")
            world_y = self._world(directory, "project-y")
            prediction = WorldPrediction(
                project="project-y", prediction_id="p1", entity_id="job", predicate="state",
                action="start", from_value="idle", predicted_value="running", confidence=1.0,
                evidence_observation_ids=(), created_at="2026-01-01T00:00:00+00:00",
            )
            with self.assertRaisesRegex(ValueError, "different world-model project"):
                world_x.score_prediction(prediction, "running")
            self.assertEqual(world_y.score_prediction(prediction, "running").absolute_match, True)

    def test_predict_next_returns_none_without_learned_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            world = self._world(directory)
            world.observe(Observation("o1", "job", "state", "idle", "test"))
            self.assertIsNone(world.predict_next("job", "state", "start"))


if __name__ == "__main__":
    unittest.main()
