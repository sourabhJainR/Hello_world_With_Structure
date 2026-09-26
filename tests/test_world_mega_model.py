from portable.capability_evolution import CapabilityEvolution
from portable.execution_strategy import ExecutionPathway, execution_strategy
from portable.persistent_memory import PersistentMemory
from portable.world_model import Observation
from portable.world_mega_model import WorldMegaModel


def _memory(tmp_path):
    return PersistentMemory(tmp_path / "mega.db", project="mega-test")


def test_world_mega_model_observe_predict_and_plan(tmp_path):
    memory = _memory(tmp_path)
    model = WorldMegaModel(memory, "mega-test")
    model.observe(Observation("o1", "repo", "state", "ready", "test", observed_at="2026-01-01T00:00:00+00:00"))
    model.observe(Observation("o2", "repo", "state", "done", "test", observed_at="2026-01-02T00:00:00+00:00",
                               properties={"action": "run"}))
    model.observe(Observation("o3", "repo", "state", "ready", "test", observed_at="2026-01-03T00:00:00+00:00"))
    model.observe(Observation("o4", "repo", "state", "done", "test", observed_at="2026-01-04T00:00:00+00:00",
                               properties={"action": "run"}))
    prediction = model.predict("repo", "state", "run", current_value="ready")
    assert prediction is not None
    assert prediction.predicted_value == "done"
    plan = model.plan("run repository task", capability="testing")
    assert plan.strategy == "default"
    assert plan.cognitive is not None


def test_world_mega_model_detects_verified_repeated_gap(tmp_path):
    memory = _memory(tmp_path)
    model = WorldMegaModel(memory, "mega-test")
    experiences = [
        {"outcome": "failed", "verified": True, "evidence_ids": ["e1"]},
        {"outcome": "failed", "verified": True, "evidence_ids": ["e2"]},
        {"outcome": "failed", "verified": True, "evidence_ids": ["e3"]},
    ]
    decision = model.detect_capability_gap("coding", "schema-debugging", experiences)
    assert decision.status == "propose"
    assert decision.proposal is not None


def test_world_mega_model_rejects_unverified_promotion(tmp_path):
    memory = _memory(tmp_path)
    model = WorldMegaModel(memory, "mega-test")
    from portable.continual_learning import BenchmarkObservation
    observation = BenchmarkObservation(
        "case-1", "plan", "prov", "passed", "passed", 0.99, 1, 0, 0,
        verified=False,
    )
    result = model.gate_promotion(observation)
    assert result.accepted is False
    assert result.action == "reject"


def test_strategy_unknown_is_safe_default():
    assert execution_strategy("unknown").name == "default"
    assert execution_strategy("unknown").known is False
