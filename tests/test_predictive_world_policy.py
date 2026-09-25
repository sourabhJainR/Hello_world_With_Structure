from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from portable.persistent_memory import PersistentMemory
from portable.predictive_world_policy import PredictiveWorldPolicy
from portable.world_model import Observation, WorldModel


class PredictiveWorldPolicyTests(unittest.TestCase):
    def _world(self):
        root = Path(tempfile.mkdtemp())
        return WorldModel(PersistentMemory(root / "memory.db", require_approval=False), "test")

    def _observe(self, world, oid, value, action):
        world.observe(
            Observation(
                observation_id=oid,
                entity_id="agent-1",
                predicate="lane",
                value=value,
                source="test",
                properties={"action": action},
            )
        )

    def test_abstains_without_transition_evidence(self):
        world = self._world()
        self._observe(world, "1", "agent", "noop")
        signal = PredictiveWorldPolicy(world).forecast("agent-1", "lane", "run")
        self.assertTrue(signal.abstained)
        self.assertIn("insufficient", signal.reason)

    def test_forecasts_repeated_transition(self):
        world = self._world()
        self._observe(world, "1", "agent", "warm")
        self._observe(world, "2", "local", "switch")
        self._observe(world, "3", "agent", "switch")
        self._observe(world, "4", "local", "switch")
        self._observe(world, "5", "agent", "switch")
        signal = PredictiveWorldPolicy(world, min_samples=2, min_confidence=0.65).forecast(
            "agent-1", "lane", "switch", current_value="agent"
        )
        self.assertFalse(signal.abstained)
        self.assertIsNotNone(signal.prediction)
        self.assertEqual(signal.prediction.predicted_value, "local")
        self.assertGreaterEqual(signal.confidence, 0.65)

    def test_low_confidence_abstains(self):
        world = self._world()
        self._observe(world, "1", "agent", "warm")
        self._observe(world, "2", "local", "switch")
        self._observe(world, "3", "agent", "switch")
        signal = PredictiveWorldPolicy(world, min_samples=1, min_confidence=0.8).forecast(
            "agent-1", "lane", "switch", current_value="agent"
        )
        self.assertTrue(signal.abstained)
        self.assertIsNotNone(signal.prediction)

    def test_prediction_can_be_scored_by_canonical_world_model(self):
        world = self._world()
        self._observe(world, "1", "agent", "warm")
        self._observe(world, "2", "local", "switch")
        self._observe(world, "3", "agent", "switch")
        self._observe(world, "4", "local", "switch")
        self._observe(world, "5", "agent", "switch")
        signal = PredictiveWorldPolicy(world, min_samples=2).forecast(
            "agent-1", "lane", "switch", current_value="agent"
        )
        self.assertFalse(signal.abstained)
        error = world.score_prediction(signal.prediction, "agent")
        self.assertFalse(error.absolute_match)
        self.assertEqual(error.prediction_id, signal.prediction.prediction_id)


if __name__ == "__main__":
    unittest.main()
