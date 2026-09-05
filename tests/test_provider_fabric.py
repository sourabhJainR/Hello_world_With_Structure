from pathlib import Path

from portable.lifecycle_hooks import HookBus, HookDecision, HookEvent, HookPhase
from portable.provider_fabric import CapabilityRequest, ProviderCapability, ProviderFabric
from portable.session_state import SessionCheckpoint, SessionStore


def test_provider_fabric_prefers_native_capability(tmp_path: Path):
    fabric = ProviderFabric(tmp_path)
    providers = {
        "claude": ProviderCapability("claude", "/bin/claude", "test", ("agent", "subagent", "hooks"), ("test",)),
        "codex": ProviderCapability("codex", "/bin/codex", "test", ("agent",), ("test",)),
    }
    decision = fabric.route(CapabilityRequest("subagent", ("codex", "claude")), providers)
    assert decision.provider == "claude"
    assert decision.native is True


def test_provider_fabric_falls_back_to_aer(tmp_path: Path):
    fabric = ProviderFabric(tmp_path)
    decision = fabric.route(CapabilityRequest("background_execution", ("codex",)))
    assert decision.provider == "aer"
    assert decision.native is False


def test_hook_bus_fails_closed_and_preserves_annotations():
    bus = HookBus()
    bus.register(HookPhase.BEFORE_TOOL, lambda event: HookDecision(True, annotations={"audited": True}))
    event = HookEvent(HookPhase.BEFORE_TOOL, "s1", "t1")
    decision = bus.emit(event)
    assert decision.allow is True
    assert decision.annotations["audited"] is True

    bus.register(HookPhase.BEFORE_TOOL, lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    denied = bus.emit(event)
    assert denied.allow is False


def test_session_checkpoint_survives_new_store_instance(tmp_path: Path):
    store = SessionStore(tmp_path)
    checkpoint = SessionCheckpoint("session-1", "task-1", "project-a", "verify", ["plan", "build"], ["test"], "claude")
    store.save(checkpoint)

    restored = SessionStore(tmp_path).load("session-1")
    assert restored is not None
    assert restored.remaining_batches == ["test"]
    assert restored.state_digest

    recovered = SessionStore(tmp_path).recover("session-1", next_stage="test")
    assert recovered is not None
    assert recovered.stage == "test"
    assert recovered.attempt == 1
