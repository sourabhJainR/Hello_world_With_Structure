from pathlib import Path

from portable.agency_release_lifecycle import ArtifactStore
from portable.agency_regression_loop import PromotionDecision


def test_shadow_canary_promote_and_rollback(tmp_path: Path):
    source1 = tmp_path / "a.txt"
    source2 = tmp_path / "b.txt"
    source1.write_text("one", encoding="utf-8")
    source2.write_text("two", encoding="utf-8")
    store = ArtifactStore(tmp_path / "release")
    a = store.stage(source1, "v1")
    assert store.stage(source1, "v1-repeat").digest == a.digest
    b = store.stage(source2, "v2")

    shadow = store.apply_decision(PromotionDecision("shadow", "quality", 0.8, True, "r1"), a)
    assert shadow.action == "shadow"
    assert store.state()["current"] is None

    canary = store.apply_decision(PromotionDecision("canary", "staged", 0.95, True, "r2"), b)
    assert canary.action == "canary"
    assert store.state()["canary"]["artifact_id"] == "v2"
    assert store.state()["current"] is None

    promoted = store.apply_decision(PromotionDecision("promote", "passed", 0.99, True, "r3"), a)
    assert promoted.action == "promote"
    assert store.state()["current"]["artifact_id"] == "v1"

    promoted2 = store.apply_decision(PromotionDecision("promote", "passed", 0.99, True, "r4"), b)
    assert promoted2.action == "promote"
    assert store.state()["current"]["artifact_id"] == "v2"

    rolled = store.apply_decision(PromotionDecision("rollback", "regression failed", 0.1, False, "r5"))
    assert rolled.action == "rollback"
    assert store.state()["current"]["artifact_id"] == "v1"


def test_rollback_without_active_artifact_is_recorded(tmp_path: Path):
    store = ArtifactStore(tmp_path / "release")
    state = store.transition("rollback", None, "failed candidate")
    assert state.action == "rollback"
    assert state.artifact_id is None
