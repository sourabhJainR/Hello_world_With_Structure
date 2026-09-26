from portable.autonomous_capability_invention import (
    AutonomousCapabilityInvention,
    CapabilityComposition,
    HoldoutResult,
    SafetyResult,
)
from portable.persistent_memory import PersistentMemory


def memory(tmp_path):
    return PersistentMemory(tmp_path / "invention.db", project="invention-test")


def incumbent():
    return CapabilityComposition("default:local:standard:verify", ("verify",), "default", "local", "standard")


def result(candidate, holdout_id):
    score = {"h1": 0.91, "h2": 0.90, "h3": 0.92}[holdout_id] if "compose" in candidate.id else 0.60
    return HoldoutResult(holdout_id, score, 0.80, True, True, (f"e-{candidate.id}-{holdout_id}",))


def test_composition_search_is_bounded_and_recombinatorial():
    rows = AutonomousCapabilityInvention.compose(
        ("parse", "reason", "verify"), strategy="default",
        resource_lanes=("local", "agent"),
        verification_depths=("standard", "deep"), max_candidates=8,
    )
    assert rows
    assert len(rows) <= 8
    assert any(len(row.capabilities) > 1 for row in rows)


def test_invention_graduates_only_a_verified_improvement(tmp_path):
    engine = AutonomousCapabilityInvention(memory(tmp_path), "invention-test", max_candidates=8)
    receipt = engine.invent(
        "schema-debugging",
        incumbent=incumbent(),
        available_capabilities=("parse", "reason", "compose", "verify"),
        holdout_ids=("h1", "h2", "h3"),
        evaluate=result,
        safety_gate=lambda candidate: SafetyResult(True, (f"safety-{candidate.id}",)),
        trigger_evidence=("trigger-1", "trigger-2", "trigger-3"),
    )
    assert receipt.status == "graduated"
    assert receipt.graduated
    assert receipt.selected is not None
    assert receipt.selected.improvement >= 0.02


def test_invention_rejects_regression(tmp_path):
    engine = AutonomousCapabilityInvention(memory(tmp_path), "invention-test", max_candidates=4)
    def evaluate(candidate, holdout_id):
        return HoldoutResult(holdout_id, 0.70, 0.80, True, True, (f"e-{holdout_id}",))
    receipt = engine.invent(
        "hard-task",
        incumbent=incumbent(),
        available_capabilities=("parse", "reason"),
        holdout_ids=("h1", "h2", "h3"),
        evaluate=evaluate,
        safety_gate=lambda candidate: SafetyResult(True),
    )
    assert receipt.status == "rejected"
    assert not receipt.graduated


def test_invention_rejects_safety_failure(tmp_path):
    engine = AutonomousCapabilityInvention(memory(tmp_path), "invention-test")
    receipt = engine.invent(
        "unsafe-task",
        incumbent=incumbent(),
        available_capabilities=("parse", "reason"),
        holdout_ids=("h1", "h2", "h3"),
        evaluate=lambda candidate, holdout_id: HoldoutResult(holdout_id, 0.95, 0.80, True, True, ("e",)),
        safety_gate=lambda candidate: SafetyResult(False, reasons=("unsafe",)),
    )
    assert receipt.status == "rejected"
    assert any("safety" in reason for reason in receipt.selected.reasons) if receipt.selected else True
