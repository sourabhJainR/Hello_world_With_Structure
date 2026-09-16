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
from .agent_memory import AgentMemory
from .context_engine import ContextEngine, ContextItem, ContextPolicy, Handoff, handoff_from_output
from .dream_memory import DreamMemory
from .automation_scheduler import AutomationScheduler, Schedule
from .output_quality import OutputQualityGate, QualityResult
from .feedback_loop import BoundedLoop, LoopAction, LoopDefinition, LoopPass, LoopRunReceipt, VerificationResult
from .agency_provenance import ProvenanceLedger, ProvenanceRecord
from .engineering_design_guard import DesignDimension, DesignFinding, DesignReviewReceipt, EngineeringDesignGuard, FindingSeverity
from .agency_state_graph import Checkpoint, CompiledStateGraph, GraphEvent, GraphInterrupt, GraphRun, InMemoryCheckpointStore, RetryPolicy, StateGraph
from .decision_fabric import ChoiceDecision, DecisionBatch, DecisionFabric, DecisionPolicy, DecisionQuestion, NoulDecision, PolicyDecision, ScoreDecision
from .recursive_agency import AgencyReceipt, CycleObservation, RecursiveAgency, WorkItem
from .repository_intelligence import (
    PackedFile, RepositoryAnswer, RepositoryEvidence, RepositoryIntelligence, RepositoryMap, RepositoryPack, render_compact,
)
from .agent_patterns import (
    ConsensusResult,
    EvidenceItem,
    MixtureOfAgents,
    OneChangeOptimizer,
    OptimizationResult,
    OptimizationRound,
    ResearchPlan,
    ResearchPlanner,
    ResearchTask,
    RouteDecision,
    RouteRequest,
    ScopeChecker,
    ScopeFinding,
    ScopeReport,
    Specialist,
    SpecialistRouter,
)
from .world_model import Observation, WorldFact, WorldModel
from .hypothesis_engine import BeliefEvidence, Hypothesis, HypothesisEngine
from .reasoning_ledger import ReasoningLedger, ReasoningRecord
from .causal_model import CausalLink, CausalModel
from .goal_manager import Goal, GoalManager
from .information_planner import InformationAction, InformationPlan, InformationPlanner

__all__ = [
    "main", "AdaptiveRuntime", "HookBus", "HookDecision", "HookEvent", "HookPhase", "HookedExecution",
    "CapabilityRequest", "ProviderCapability", "ProviderFabric", "RoutingDecision", "SessionCheckpoint", "SessionStore",
    "ImpactRecord", "ImpactReport", "analyze", "Task", "TaskPlan", "STATUSES", "PRIORITIES",
    "CAPABILITIES", "Capability", "CapabilityFabric", "ProviderAdapter", "ProviderAdapterRegistry",
    "MemoryRecord", "PersistentMemory", "AgentMemory", "ContextEngine", "ContextItem", "ContextPolicy",
    "Handoff", "handoff_from_output", "DreamMemory", "AutomationScheduler", "Schedule", "OutputQualityGate", "QualityResult",
    "BoundedLoop", "LoopAction", "LoopDefinition", "LoopPass", "LoopRunReceipt", "VerificationResult",
    "ProvenanceLedger", "ProvenanceRecord", "DesignDimension", "DesignFinding", "DesignReviewReceipt",
    "EngineeringDesignGuard", "FindingSeverity", "Checkpoint", "CompiledStateGraph", "GraphEvent",
    "GraphInterrupt", "GraphRun", "InMemoryCheckpointStore", "RetryPolicy", "StateGraph",
    "ChoiceDecision", "DecisionBatch", "DecisionFabric", "DecisionPolicy", "DecisionQuestion", "NoulDecision", "PolicyDecision", "ScoreDecision",
    "AgencyReceipt", "CycleObservation", "RecursiveAgency", "WorkItem",
    "PackedFile", "RepositoryPack", "RepositoryEvidence", "RepositoryAnswer", "RepositoryIntelligence", "RepositoryMap", "render_compact",
    "Specialist", "SpecialistRouter", "RouteRequest", "RouteDecision",
    "ResearchTask", "ResearchPlan", "ResearchPlanner", "EvidenceItem", "ConsensusResult", "MixtureOfAgents",
    "OptimizationRound", "OptimizationResult", "OneChangeOptimizer", "ScopeFinding", "ScopeReport", "ScopeChecker",
    "Observation", "WorldFact", "WorldModel", "BeliefEvidence", "Hypothesis", "HypothesisEngine",
    "ReasoningLedger", "ReasoningRecord", "CausalLink", "CausalModel", "Goal", "GoalManager",
    "InformationAction", "InformationPlan", "InformationPlanner",
]
