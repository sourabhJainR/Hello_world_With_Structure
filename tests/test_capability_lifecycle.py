from portable.capability_lifecycle import CapabilityLifecycle
from portable.persistent_memory import PersistentMemory


def test_capability_promotes_after_bounded_safe_canaries(tmp_path):
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    lifecycle = CapabilityLifecycle(memory, "p", min_canaries=3, regression_tolerance=0.02)
    start = lifecycle.begin("candidate-a", baseline_score=0.70)
    assert start.state == "canary"
    assert lifecycle.record_canary("candidate-a", score=0.71, evidence_id="e1").state == "canary"
    assert lifecycle.record_canary("candidate-a", score=0.73, evidence_id="e2").state == "canary"
    final = lifecycle.record_canary("candidate-a", score=0.72, evidence_id="e3")
    assert final.state == "promoted"
    assert final.canary_count == 3


def test_capability_rolls_back_on_regression_or_safety_failure(tmp_path):
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    lifecycle = CapabilityLifecycle(memory, "p", min_canaries=3, regression_tolerance=0.02)
    lifecycle.begin("candidate-b", baseline_score=0.80)
    result = lifecycle.record_canary("candidate-b", score=0.70, evidence_id="r1")
    assert result.state == "rolled_back"

    lifecycle.begin("candidate-c", baseline_score=0.80)
    result = lifecycle.record_canary("candidate-c", score=0.90, evidence_id="s1", safe=False)
    assert result.state == "rolled_back"


def test_duplicate_canary_evidence_is_rejected(tmp_path):
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    lifecycle = CapabilityLifecycle(memory, "p")
    lifecycle.begin("candidate-d", baseline_score=0.80)
    lifecycle.record_canary("candidate-d", score=0.81, evidence_id="same")
    try:
        lifecycle.record_canary("candidate-d", score=0.82, evidence_id="same")
    except ValueError as exc:
        assert "already recorded" in str(exc)
    else:
        raise AssertionError("duplicate evidence must be rejected")
