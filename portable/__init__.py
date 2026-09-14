"""Portable AER runtime package."""

from .adaptive_runtime import AdaptiveRuntime
from .aer_runtime import main
from .impact_analysis import ImpactRecord, ImpactReport, analyze
from .lifecycle_hooks import HookBus, HookDecision, HookEvent, HookPhase, HookedExecution
from .provider_fabric import CapabilityRequest, ProviderCapability, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore
from .task_planner import PRIORITIES, STATUSES, Task, TaskPlan
from .capability_fabric import CAPABILITIES, Capability, CapabilityFabric, ProviderAdapter, ProviderAdapterRegistry
from .persistent_memory import MemoryRecord, PersistentMemory
from .automation_scheduler import AutomationScheduler, Schedule
from .output_quality import OutputQualityGate, QualityResult
from .feedback_loop import BoundedLoop, LoopAction, LoopDefinition, LoopPass, LoopRunReceipt, VerificationResult
from .agency_provenance import ProvenanceLedger, ProvenanceRecord
from .engineering_design_guard import DesignDimension, DesignFinding, DesignReviewReceipt, EngineeringDesignGuard, FindingSeverity
from .agency_state_graph import Checkpoint, CompiledStateGraph, GraphEvent, GraphInterrupt, GraphRun, InMemoryCheckpointStore, RetryPolicy, StateGraph

__all__ = [
    "main", "AdaptiveRuntime", "HookBus", "HookDecision", "HookEvent", "HookPhase", "HookedExecution",
    "CapabilityRequest", "ProviderCapability", "ProviderFabric", "RoutingDecision", "SessionCheckpoint", "SessionStore",
    "ImpactRecord", "ImpactReport", "analyze", "Task", "TaskPlan", "STATUSES", "PRIORITIES",
    "CAPABILITIES", "Capability", "CapabilityFabric", "ProviderAdapter", "ProviderAdapterRegistry",
    "MemoryRecord", "PersistentMemory", "AutomationScheduler", "Schedule", "OutputQualityGate", "QualityResult",
    "BoundedLoop", "LoopAction", "LoopDefinition", "LoopPass", "LoopRunReceipt", "VerificationResult",
    "ProvenanceLedger", "ProvenanceRecord", "DesignDimension", "DesignFinding", "DesignReviewReceipt",
    "EngineeringDesignGuard", "FindingSeverity", "Checkpoint", "CompiledStateGraph", "GraphEvent",
    "GraphInterrupt", "GraphRun", "InMemoryCheckpointStore", "RetryPolicy", "StateGraph",
]
