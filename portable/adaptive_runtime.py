"""Reusable facade that composes AER orchestration and agent capabilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .automation_scheduler import AutomationScheduler
from .capability_fabric import Capability, CapabilityFabric, ProviderAdapter, ProviderAdapterRegistry
from .context_graph import ContextGraph
from .context_resolver import ContextResolution, ContextResolver
from .cognitive_loop import CognitiveEpisodeReceipt, CognitiveLoop
from .cognitive_runtime import CognitiveRuntime
from .lifecycle_hooks import HookBus, HookPhase, HookedExecution
from .orchestration import Graph, OrchestrationRun, Orchestrator
from .output_quality import OutputQualityGate, QualityResult
from .persistent_memory import PersistentMemory
from .provider_fabric import CapabilityRequest, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore
from .trigger_runtime import TriggerEvent, TriggerRuntime


class AdaptiveRuntime:
    """Single AER composition point for provider, capability and durable state."""

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
        provider_adapters: ProviderAdapterRegistry | None = None,
        max_total_attempts: int = 32,
    ) -> None:
        self.orchestrator = Orchestrator(graph, max_total_attempts=max_total_attempts)
        self.session_store = session_store or SessionStore()
        self.provider_fabric = provider_fabric or ProviderFabric()
        self.hooks = hooks or HookBus()
        self.capability_fabric = capability_fabric or CapabilityFabric()
        aer_state = Path.home() / ".aer"
        self.persistent_memory = persistent_memory or PersistentMemory(aer_state / "memory" / "memory.db")
        self.automation_scheduler = automation_scheduler or AutomationScheduler(aer_state / "automation" / "automation.db")
        self.output_quality = output_quality or OutputQualityGate()
        self.provider_adapters = provider_adapters or ProviderAdapterRegistry()
        self.trigger_runtime = TriggerRuntime(self.automation_scheduler)
        self._cognitive_loop = CognitiveLoop()
        self.last_cognitive_episode: CognitiveEpisodeReceipt | None = None

    def capability(self, name: str, preferred: tuple[str, ...] = ()) -> RoutingDecision:
        return self.provider_fabric.route(CapabilityRequest(name, preferred))

    def plan_capabilities(self, requested: Iterable[str], *, network_allowed: bool,
                          sandbox_available: bool = True, max_risk: str = "high") -> list[Capability]:
        return self.capability_fabric.plan(
            requested, network_allowed=network_allowed,
            sandbox_available=sandbox_available, max_risk=max_risk,
        )

    def register_provider_adapter(self, name: str, capabilities: Iterable[str], *, priority: int = 0) -> None:
        self.provider_adapters.register(ProviderAdapter(name, frozenset(capabilities), priority=priority))

    def resolve_provider_adapter(self, required: Iterable[str], preferred: tuple[str, ...] = ()) -> ProviderAdapter:
        return self.provider_adapters.resolve(required, preferred)

    def quality_check(self, *, acceptance_met: bool, verification_passed: bool,
                      evidence_count: int, diff_clean: bool, scope_clean: bool,
                      unresolved: int = 0) -> QualityResult:
        return self.output_quality.evaluate(
            acceptance_met=acceptance_met,
            verification_passed=verification_passed,
            evidence_count=evidence_count,
            diff_clean=diff_clean,
            scope_clean=scope_clean,
            unresolved=unresolved,
        )

    def resolve_context(self, project_root: Path | str, task: str, *, node_id: str | None = None,
                        workspace_id: str | None = None, required: Sequence[str] = (),
                        memory_limit: int = 12, graph_limit: int = 24) -> ContextResolution:
        """Resolve durable context through the canonical memory/graph path."""
        project_key = self.session_store.project_key(project_root)
        graph = ContextGraph(self.persistent_memory, project_key)
        resolver = ContextResolver(self.persistent_memory, graph)
        return resolver.resolve(task, node_id=node_id, workspace_id=workspace_id,
                                required=required, memory_limit=memory_limit, graph_limit=graph_limit)

    def cognition(self, project_root: Path | str) -> CognitiveRuntime:
        """Return the project-scoped cognitive layer without replacing orchestration."""
        project_key = self.session_store.project_key(project_root)
        return CognitiveRuntime.create(self.persistent_memory, project_key)

    def emit_trigger(self, kind: str, payload: Mapping[str, Any], *, event_id: str | None = None,
                     max_attempts: int = 3) -> TriggerEvent:
        return self.trigger_runtime.emit(kind, payload, event_id=event_id, max_attempts=max_attempts)

    def dispatch_triggers(self, handler: Any, *, limit: int = 20) -> list[Any]:
        """Dispatch claimed triggers to a caller-owned normal orchestration handler."""
        return self.trigger_runtime.dispatch_due(handler, limit=limit)

    def run(
        self,
        *,
        session_id: str,
        task_id: str,
        project_root: Path | str,
        intent: str,
        provider: str | None = None,
        context: Mapping[str, Any] | None = None,
        context_node_id: str | None = None,
        workspace_id: str | None = None,
        required_context: Sequence[str] = (),
        enrich_context: bool = False,
    ) -> OrchestrationRun:
        project_key = self.session_store.project_key(project_root)
        provider_name = provider or "aer"
        execution = HookedExecution(self.hooks, session_id, provider_name)
        start = execution.gate(HookPhase.SESSION_START, task_id=task_id, payload={"project_key": project_key})
        if not start.allow:
            raise RuntimeError(f"session_start vetoed: {start.reason}")
        checkpoint = SessionCheckpoint(
            session_id=session_id, task_id=task_id, project_key=project_key,
            stage="execute", remaining_batches=["verify", "review", "learn"],
            active_provider=provider_name,
        )
        self.session_store.save(checkpoint)
        episode = self._cognitive_loop.begin(project_key, task_id, intent)
        self._cognitive_loop.cognitive = self.cognition(project_root)
        try:
            before = execution.gate(HookPhase.BEFORE_AGENT, task_id=task_id)
            if not before.allow:
                raise RuntimeError(f"before_agent vetoed: {before.reason}")
            self._cognitive_loop.observe(episode, {"event": "before_agent", "status": "running"})
            effective_context = dict(context or {})
            if enrich_context:
                resolution = self.resolve_context(
                    project_root, intent, node_id=context_node_id,
                    workspace_id=workspace_id, required=required_context,
                )
                effective_context["aer_context_pack"] = resolution.pack
                effective_context["aer_context_digest"] = resolution.digest
                effective_context["aer_context_omitted"] = list(resolution.omitted)
                self._cognitive_loop.observe(episode, {"event": "context_resolved", "digest": resolution.digest})
            result = self.orchestrator.run(task_id, intent, effective_context)
            self._cognitive_loop.observe(episode, {"event": "execution_completed", "status": result.status.value})
            after = execution.gate(HookPhase.AFTER_AGENT, task_id=task_id, payload={"status": result.status.value})
            if not after.allow:
                raise RuntimeError(f"after_agent vetoed: {after.reason}")
            checkpoint.stage = "complete"
            checkpoint.completed_batches = ["execute", "verify", "review", "learn"]
            checkpoint.remaining_batches = []
            checkpoint.last_error = None
            self.session_store.save(checkpoint)
            self.last_cognitive_episode = self._cognitive_loop.complete(episode, result.status.value)
            execution.gate(HookPhase.SESSION_END, task_id=task_id, payload={"status": result.status.value})
            return result
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._cognitive_loop.observe(episode, {"event": "execution_error", "status": "failed", "error": error})
            self.last_cognitive_episode = self._cognitive_loop.complete(episode, "failed", error)
            checkpoint.last_error = error
            checkpoint.attempt += 1
            self.session_store.save(checkpoint)
            execution.gate(HookPhase.RECOVERY, task_id=task_id, payload={"error": checkpoint.last_error})
            raise

    def recover(self, session_id: str, next_stage: str = "execute") -> SessionCheckpoint | None:
        return self.session_store.recover(session_id, next_stage=next_stage)


__all__ = ["AdaptiveRuntime"]
