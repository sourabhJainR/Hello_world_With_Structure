"""Portable AER runtime package."""

from .adaptive_runtime import AdaptiveRuntime
from .aer_runtime import main
from .impact_analysis import ImpactRecord, ImpactReport, analyze
from .lifecycle_hooks import HookBus, HookDecision, HookEvent, HookPhase, HookedExecution
from .provider_fabric import CapabilityRequest, ProviderCapability, ProviderFabric, RoutingDecision
from .session_state import SessionCheckpoint, SessionStore
from .task_planner import PRIORITIES, STATUSES, Task, TaskPlan
from .capability_fabric import CAPABILITIES, Capability, CapabilityFabric
from .persistent_memory import MemoryRecord, PersistentMemory
from .automation_scheduler import AutomationScheduler, RunClaim, Schedule
from .output_quality import OutputQualityGate, QualityResult

__all__ = [
    "main", "AdaptiveRuntime", "HookBus", "HookDecision", "HookEvent", "HookPhase", "HookedExecution",
    "CapabilityRequest", "ProviderCapability", "ProviderFabric", "RoutingDecision", "SessionCheckpoint", "SessionStore",
    "ImpactRecord", "ImpactReport", "analyze", "Task", "TaskPlan", "STATUSES", "PRIORITIES",
    "CAPABILITIES", "Capability", "CapabilityFabric", "MemoryRecord", "PersistentMemory",
    "AutomationScheduler", "RunClaim", "Schedule", "OutputQualityGate", "QualityResult",
]
