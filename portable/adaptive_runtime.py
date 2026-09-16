"""Reusable facade that composes AER orchestration and agent capabilities."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .automation_scheduler import AutomationScheduler
from .capability_fabric import Capability, CapabilityFabric, ProviderAdapter, ProviderAdapterRegistry
from .context_graph import ContextGraph
from .context_resolver import ContextResolution, ContextResolver
from .cognitive_controller import CognitiveController
from .cognitive_learning import BeliefContext, CognitiveLearningLoop
from .cognitive_loop import CognitiveEpisodeReceipt, CognitiveLoop
from .cognitive_runtime import CognitiveRuntime
from .hypothesis_engine import BeliefEvidence
from .information_planner import InformationAction
from .lifecycle_hooks import HookBus, HookPhase, HookedExecution
from .orchestration import Graph, OrchestrationRun, Orchestrator
from .output_quality import OutputQualityGate, QualityResult
from .persistent_memory import PersistentMemory
from .provider_fabric import CapabilityRequest, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore
from .trigger_runtime import TriggerEvent, TriggerRuntime
from .world_model import PredictionError


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
        self.last_cognitive_episode: CognitiveEpisodeReceipt | None = None
        self.last_cognitive_plan: dict[str, object] | None = None
        self.last_learning_signal = None

    def capability(self, name: str, preferred: tuple[str, ...] = ()) -> RoutingDecision:
        return self.provider_fabric.route(CapabilityRequest(name, preferred))

    def plan_capabilities(self, requested: Iterable[str], *, network_allowed: bool,
                          sandbox_available: bool = True, max_risk: str = "high") -> list[Capability]:
        return self.capability_fabric.plan(requested, network_allowed=network_allowed,
                                           sandbox_available=sandbox_available, max_risk=max_risk)

    def register_provider_adapter(self, name: str, capabilities: Iterable[str], *, priority: int = 0) -> None:
        self.provider_adapters.register(ProviderAdapter(name, frozenset(capabilities), priority=priority))

    def resolve_provider_adapter(self, required: Iterable[str], preferred: tuple[str, ...] = ()) -> ProviderAdapter:
        return self.provider_adapters.resolve(required, preferred)

    def quality_check(self, *, acceptance_met: bool, verification_passed: bool,
                      evidence_count: int, diff_clean: bool, scope_clean: bool,
                      unresolved: int = 0) -> QualityResult:
        return self.output_quality.evaluate(acceptance_met=acceptance_met, verification_passed=verification_passed,
                                            evidence_count=evidence_count, diff_clean=diff_clean,
                                            scope_clean=scope_clean, unresolved=unresolved)

    def resolve_context(self, project_root: Path | str, task: str, *, node_id: str | None = None,
                        workspace_id: str | None = None, required: Sequence[str] = (),
                        memory_limit: int = 12, graph_limit: int = 24) -> ContextResolution:
        project_key = self.session_store.project_key(project_root)
        graph = ContextGraph(self.persistent_memory, project_key)
        resolver = ContextResolver(self.persistent_memory, graph)
        return resolver.resolve(task, node_id=node_id, workspace_id=workspace_id, required=required,
                                memory_limit=memory_limit, graph_limit=graph_limit)

    def cognition(self, project_root: Path | str) -> CognitiveRuntime:
        project_key = self.session_store.project_key(project_root)
        return CognitiveRuntime.create(self.persistent_memory, project_key)

    def emit_trigger(self, kind: str, payload: Mapping[str, Any], *, event_id: str | None = None,
                     max_attempts: int = 3) -> TriggerEvent:
        return self.trigger_runtime.emit(kind, payload, event_id=event_id, max_attempts=max_attempts)

    def dispatch_triggers(self, handler: Any, *, limit: int = 20) -> list[Any]:
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
        enrich_cognition: bool = True,
        cognitive_capability: str | None = None,
        cognitive_uncertainty: float = 0.5,
        cognitive_information_actions: tuple[InformationAction, ...] = (),
        cognitive_entity_id: str | None = None,
        cognitive_predicate: str | None = None,
        cognitive_action: str | None = None,
        cognitive_current_value: object | None = None,
        cognitive_beliefs: tuple[BeliefContext, ...] = (),
        cognitive_belief_limit: int = 8,
        cognitive_belief_evidence: tuple[BeliefEvidence, ...] = (),
        cognitive_actual_value: object | None = None,
        learning_evidence: tuple[str, ...] = (),
        learning_context: str | None = None,
    ) -> OrchestrationRun:
        project_key = self.session_store.project_key(project_root)
        provider_name = provider or "aer"
        execution = HookedExecution(self.hooks, session_id, provider_name)
        start = execution.gate(HookPhase.SESSION_START, task_id=task_id, payload={"project_key": project_key})
        if not start.allow:
            raise RuntimeError(f"session_start vetoed: {start.reason}")
        checkpoint = SessionCheckpoint(session_id=session_id, task_id=task_id, project_key=project_key,
                                       stage="execute", remaining_batches=["verify", "review", "learn"], active_provider=provider_name)
        self.session_store.save(checkpoint)
        cognitive_runtime = self.cognition(project_root)
        cognitive_loop = CognitiveLoop(cognitive_runtime)
        learning_loop = CognitiveLearningLoop(self.persistent_memory, project_key, self_model=cognitive_runtime.self_model)
        episode = cognitive_loop.begin(project_key, task_id, intent)
        prediction_error: PredictionError | None = None
        cognitive_plan_payload: dict[str, object] | None = None
        try:
            before = execution.gate(HookPhase.BEFORE_AGENT, task_id=task_id)
            if not before.allow:
                raise RuntimeError(f"before_agent vetoed: {before.reason}")
            cognitive_loop.observe(episode, {"event": "before_agent", "status": "running"})
            effective_context = dict(context or {})
            if enrich_context:
                resolution = self.resolve_context(project_root, intent, node_id=context_node_id,
                                                  workspace_id=workspace_id, required=required_context)
                effective_context["aer_context_pack"] = resolution.pack
                effective_context["aer_context_digest"] = resolution.digest
                effective_context["aer_context_omitted"] = list(resolution.omitted)
                cognitive_loop.observe(episode, {"event": "context_resolved", "digest": resolution.digest})
            if enrich_cognition:
                effective_context = CognitiveController(cognitive_runtime).enrich_context(
                    intent, capability=cognitive_capability, uncertainty=cognitive_uncertainty,
                    information_actions=cognitive_information_actions, entity_id=cognitive_entity_id,
                    predicate=cognitive_predicate, action=cognitive_action,
                    current_value=cognitive_current_value, beliefs=cognitive_beliefs,
                    belief_limit=cognitive_belief_limit, context=effective_context,
                )
                cognitive_plan_payload = dict(effective_context["aer_cognitive_plan"])  # type: ignore[arg-type]
                self.last_cognitive_plan = dict(cognitive_plan_payload)
                cognitive_loop.observe(episode, {
                    "event": "cognitive_plan_created",
                    "belief_count": len(cognitive_plan_payload.get("belief_ids", [])),
                    "prediction_id": (cognitive_plan_payload.get("prediction") or {}).get("prediction_id")
                    if isinstance(cognitive_plan_payload.get("prediction"), dict) else None,
                })
            result = self.orchestrator.run(task_id, intent, effective_context)
            cognitive_loop.observe(episode, {"event": "execution_completed", "status": result.status.value})
            prediction = cognitive_plan_payload.get("prediction") if cognitive_plan_payload else None
            if cognitive_actual_value is not None and isinstance(prediction, dict):
                predicted_value = prediction.get("predicted_value")
                actual_digest = hashlib.sha256(json.dumps({"predicted": predicted_value, "actual": cognitive_actual_value},
                                                         sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
                prediction_error = PredictionError(
                    prediction_id=str(prediction["prediction_id"]),
                    predicted_value=predicted_value,
                    actual_value=cognitive_actual_value,
                    absolute_match=predicted_value == cognitive_actual_value,
                    error_digest=actual_digest,
                    measured_at=datetime.now(timezone.utc).isoformat(),
                )
                cognitive_loop.observe(episode, {
                    "event": "prediction_scored",
                    "prediction_id": prediction_error.prediction_id,
                    "correct": prediction_error.absolute_match,
                })
            after = execution.gate(HookPhase.AFTER_AGENT, task_id=task_id, payload={"status": result.status.value})
            if not after.allow:
                raise RuntimeError(f"after_agent vetoed: {after.reason}")
            checkpoint.stage = "complete"
            checkpoint.completed_batches = ["execute", "verify", "review", "learn"]
            checkpoint.remaining_batches = []
            checkpoint.last_error = None
            self.session_store.save(checkpoint)
            self.last_cognitive_episode = cognitive_loop.complete(episode, result.status.value)
            self.last_learning_signal = learning_loop.record(
                task_id=task_id, intent=intent, status=result.status.value, capability=cognitive_capability,
                evidence=learning_evidence, context=learning_context,
                belief_evidence=cognitive_belief_evidence, prediction_error=prediction_error,
            )
            execution.gate(HookPhase.SESSION_END, task_id=task_id, payload={"status": result.status.value})
            return result
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            cognitive_loop.observe(episode, {"event": "execution_error", "status": "failed", "error": error})
            self.last_cognitive_episode = cognitive_loop.complete(episode, "failed", error)
            self.last_learning_signal = learning_loop.record(
                task_id=task_id, intent=intent, status="failed", capability=cognitive_capability,
                evidence=learning_evidence, context=learning_context,
                belief_evidence=cognitive_belief_evidence, prediction_error=prediction_error,
            )
            checkpoint.last_error = error
            checkpoint.attempt += 1
            self.session_store.save(checkpoint)
            execution.gate(HookPhase.RECOVERY, task_id=task_id, payload={"error": checkpoint.last_error})
            raise

    def recover(self, session_id: str, next_stage: str = "execute") -> SessionCheckpoint | None:
        return self.session_store.recover(session_id, next_stage=next_stage)


__all__ = ["AdaptiveRuntime"]
