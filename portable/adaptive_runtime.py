"""Reusable AER execution facade with one capability/control-plane composition point."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from .automation_scheduler import AutomationScheduler
from .capability_fabric import Capability, CapabilityFabric
from .lifecycle_hooks import HookBus, HookPhase, HookedExecution
from .orchestration import Graph, OrchestrationRun, Orchestrator
from .output_quality import OutputQualityGate, QualityResult
from .persistent_memory import PersistentMemory
from .provider_fabric import CapabilityRequest, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore


class AdaptiveRuntime:
    """Project-neutral execution facade for long-running AI coding work.

    The facade composes AER graph execution, provider routing, hooks, durable
    session state, capability planning, persistent memory, scheduling and final
    output-quality validation without creating a second orchestration runtime.
    """

    def __init__(
        self,
        graph: Graph,
        *,
        session_store: SessionStore | None = None,
        provider_fabric: ProviderFabric | None = None,
        hooks: HookBus | None = None,
        capability_fabric: CapabilityFabric | None = None,
        persistent_memory: PersistentMemory | None = None,
        automation_scheduler: AutomationScheduler | None = None,
        output_quality: OutputQualityGate | None = None,
        max_total_attempts: int = 32,
    ) -> None:
        self.orchestrator = Orchestrator(graph, max_total_attempts=max_total_attempts)
        self.session_store = session_store or SessionStore()
        self.provider_fabric = provider_fabric or ProviderFabric()
        self.hooks = hooks or HookBus()
        self.capability_fabric = capability_fabric or CapabilityFabric.default()
        aer_state = Path.home() / ".aer"
        self.persistent_memory = persistent_memory or PersistentMemory(
            aer_state / "memory" / "memory.db", require_write_approval=True
        )
        self.automation_scheduler = automation_scheduler or AutomationScheduler(
            aer_state / "automation" / "automation.db"
        )
        self.output_quality = output_quality or OutputQualityGate()

    def capability(self, name: str, preferred: tuple[str, ...] = ()) -> RoutingDecision:
        """Route provider-native lifecycle capabilities through ProviderFabric."""
        return self.provider_fabric.route(CapabilityRequest(name, preferred))

    def plan_capabilities(
        self,
        requested: Iterable[str],
        *,
        network_allowed: bool,
        sandbox_available: bool = True,
    ) -> list[Capability]:
        """Select task-facing capabilities without duplicating provider routing."""
        return self.capability_fabric.plan(
            requested,
            network_allowed=network_allowed,
            sandbox_available=sandbox_available,
        )

    def quality_check(
        self,
        report: Mapping[str, Any],
        *,
        acceptance_met: bool,
        verification_passed: bool,
        diff_clean: bool,
        evidence_count: int,
        scope_clean: bool,
    ) -> QualityResult:
        """Apply the objective completion gate before a caller declares success."""
        return self.output_quality.evaluate(
            report,
            acceptance_met=acceptance_met,
            verification_passed=verification_passed,
            diff_clean=diff_clean,
            evidence_count=evidence_count,
            scope_clean=scope_clean,
        )

    def run(
        self,
        *,
        session_id: str,
        task_id: str,
        project_root: Path | str,
        intent: str,
        provider: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> OrchestrationRun:
        project_key = self.session_store.project_key(project_root)
        provider_name = provider or "aer"
        execution = HookedExecution(self.hooks, session_id, provider_name)
        start = execution.gate(HookPhase.SESSION_START, task_id=task_id, payload={"project_key": project_key})
        if not start.allow:
            raise RuntimeError(f"session_start vetoed: {start.reason}")

        checkpoint = SessionCheckpoint(
            session_id=session_id,
            task_id=task_id,
            project_key=project_key,
            stage="execute",
            remaining_batches=["verify", "review", "learn"],
            active_provider=provider_name,
        )
        self.session_store.save(checkpoint)
        try:
            before = execution.gate(HookPhase.BEFORE_AGENT, task_id=task_id)
            if not before.allow:
                raise RuntimeError(f"before_agent vetoed: {before.reason}")
            result = self.orchestrator.run(task_id, intent, context)
            after = execution.gate(HookPhase.AFTER_AGENT, task_id=task_id, payload={"status": result.status.value})
            if not after.allow:
                raise RuntimeError(f"after_agent vetoed: {after.reason}")
            checkpoint.stage = "complete"
            checkpoint.completed_batches = ["execute", "verify", "review", "learn"]
            checkpoint.remaining_batches = []
            checkpoint.last_error = None
            self.session_store.save(checkpoint)
            execution.gate(HookPhase.SESSION_END, task_id=task_id, payload={"status": result.status.value})
            return result
        except Exception as exc:
            checkpoint.last_error = f"{type(exc).__name__}: {exc}"
            checkpoint.attempt += 1
            self.session_store.save(checkpoint)
            execution.gate(HookPhase.RECOVERY, task_id=task_id, payload={"error": checkpoint.last_error})
            raise

    def recover(self, session_id: str, next_stage: str = "execute") -> SessionCheckpoint | None:
        return self.session_store.recover(session_id, next_stage=next_stage)

    def close(self) -> None:
        """Close persistent resources owned by this runtime instance."""
        self.persistent_memory.close()
        self.automation_scheduler.close()


__all__ = ["AdaptiveRuntime"]
