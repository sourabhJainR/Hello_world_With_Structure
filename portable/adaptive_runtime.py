"""Reusable facade that composes AER orchestration, provider routing, hooks, recovery and capabilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .hermes_capabilities import HermesCapabilityRuntime, OutputQualityGate
from .lifecycle_hooks import HookBus, HookPhase, HookedExecution
from .orchestration import Graph, OrchestrationRun, Orchestrator
from .provider_fabric import CapabilityRequest, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore


class AdaptiveRuntime:
    """Project-neutral execution facade for long-running AI coding work.

    The facade composes AER primitives plus the unified capability layer. Memory,
    skills, processes, delegation, scheduling and quality validation therefore
    share the same session and policy boundary instead of becoming sidecars.
    """

    def __init__(
        self,
        graph: Graph,
        *,
        session_store: SessionStore | None = None,
        provider_fabric: ProviderFabric | None = None,
        hooks: HookBus | None = None,
        capability_runtime: HermesCapabilityRuntime | None = None,
        max_total_attempts: int = 32,
    ) -> None:
        self.orchestrator = Orchestrator(graph, max_total_attempts=max_total_attempts)
        self.session_store = session_store or SessionStore()
        self.provider_fabric = provider_fabric or ProviderFabric()
        self.hooks = hooks or HookBus()
        self.capabilities = capability_runtime or HermesCapabilityRuntime()
        self.quality_gate = OutputQualityGate()

    def capability(self, name: str, preferred: tuple[str, ...] = ()) -> RoutingDecision:
        return self.provider_fabric.route(CapabilityRequest(name, preferred))

    def readiness(self) -> dict[str, Any]:
        """Return one auditable capability snapshot for the current runtime."""
        return self.capabilities.readiness()

    def run(
        self,
        *,
        session_id: str,
        task_id: str,
        project_root: Path | str,
        intent: str,
        provider: str | None = None,
        context: Mapping[str, Any] | None = None,
        session_messages: list[tuple[str, str]] | None = None,
    ) -> OrchestrationRun:
        project_key = self.session_store.project_key(project_root)
        provider_name = provider or "aer"
        execution = HookedExecution(self.hooks, session_id, provider_name)
        start = execution.gate(HookPhase.SESSION_START, task_id=task_id, payload={"project_key": project_key})
        if not start.allow:
            raise RuntimeError(f"session_start vetoed: {start.reason}")

        self.capabilities.discover()
        if session_messages:
            self.capabilities.session_boundary(session_id, session_messages)

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


__all__ = ["AdaptiveRuntime"]
