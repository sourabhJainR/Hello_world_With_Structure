from portable.autonomous_evolution_controller import AutonomousEvolutionController
from portable.persistent_memory import PersistentMemory


def test_repeated_unresolved_failures_trigger_invention(tmp_path):
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    controller = AutonomousEvolutionController(memory, "p", threshold=3)
    assert not controller.observe_failure("hard task", evidence_id="e1").triggered
    assert not controller.observe_failure("hard task", evidence_id="e2").triggered
    trigger = controller.observe_failure("hard task", evidence_id="e3")
    assert trigger.triggered
    assert trigger.failure_count == 3
    assert trigger.trigger_evidence == ("e1", "e2", "e3")


def test_resolved_outcome_does_not_trigger(tmp_path):
    memory = PersistentMemory(tmp_path / "memory.db", require_approval=False)
    controller = AutonomousEvolutionController(memory, "p", threshold=2)
    result = controller.observe_failure("resolved", evidence_id="e1", unresolved=False)
    assert not result.triggered
    assert result.failure_count == 0
