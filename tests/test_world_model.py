from pathlib import Path

import pytest

from portable.persistent_memory import PersistentMemory
from portable.world_model import Observation, WorldModel


def test_observations_are_durable_and_current_state_is_latest(tmp_path: Path) -> None:
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    model = WorldModel(memory, "demo")
    model.observe(Observation("o1", "service", "status", "degraded", "monitor", observed_at="2026-01-01T00:00:00+00:00", evidence=("metric-1",)))
    model.observe(Observation("o2", "service", "status", "healthy", "monitor", observed_at="2026-01-02T00:00:00+00:00", confidence=0.9))
    model.observe(Observation("o3", "service", "version", "2.0", "deploy", observed_at="2026-01-02T01:00:00+00:00"))

    assert model.current("service", "status")[0].value == "healthy"
    assert model.current("service", "status")[0].observation_id == "o2"
    assert model.current("service")[0].predicate == "status"
    assert len(model.history("service", "status")) == 2

    reopened = WorldModel(PersistentMemory(tmp_path / "memory.db", require_approval=False), "demo")
    assert reopened.current("service", "version")[0].value == "2.0"
    assert reopened.digest() == model.digest()


def test_observation_identity_is_idempotent_but_collision_is_rejected(tmp_path: Path) -> None:
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    model = WorldModel(memory, "demo")
    observation = Observation("same", "x", "state", {"ok": True}, "test", observed_at="2026-01-01T00:00:00+00:00")
    model.observe(observation)
    model.observe(observation)
    with pytest.raises(ValueError, match="different content"):
        model.observe(Observation("same", "x", "state", {"ok": False}, "test", observed_at="2026-01-01T00:00:00+00:00"))


def test_bounds_and_validation(tmp_path: Path) -> None:
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    model = WorldModel(memory, "demo", max_observations=1)
    model.observe(Observation("o1", "x", "state", True, "test"))
    with pytest.raises(ValueError, match="budget exceeded"):
        model.observe(Observation("o2", "x", "state", False, "test"))
    with pytest.raises(ValueError):
        Observation("o3", "x", "state", True, "test", confidence=1.1)
