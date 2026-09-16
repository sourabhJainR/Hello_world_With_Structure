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
from .world_model import Observation, PredictionError, WorldFact, WorldModel, WorldPrediction
from .hypothesis_engine import BeliefEvidence, Hypothesis, HypothesisEngine
from .reasoning_ledger import ReasoningLedger, ReasoningRecord
from .causal_model import CausalLink, CausalModel
from .counterfactual import CounterfactualEngine, CounterfactualQuery, CounterfactualResult
from .goal_manager import Goal, GoalManager
from .information_planner import InformationAction, InformationPlan, InformationPlanner
from .self_model import CapabilityProfile, SelfModel
from .agi_evaluation import CapabilityCase, CapabilityEvaluator, CaseResult, EvaluationReport, KINDS
from .cognitive_runtime import CognitiveRuntime
from .cognitive_loop import CognitiveEpisode, CognitiveEpisodeReceipt, CognitiveLoop
from .cognitive_controller import CognitiveController, CognitivePlan
from .learning_transfer import ConsolidationReceipt, LearningExperience, LearningTransfer, TransferCandidate
from .generalization import Abstraction, AnalogyCandidate, GeneralizationEngine
from .skill_graph import SkillGraph, SkillNode
from .curiosity import CuriosityEngine, LearningChoice, LearningNeed
from .continual_learning import BenchmarkObservation, ContinualLearningGuard, RegressionResult
from .capability_acquisition import CapabilityAcquirer, CapabilityNeed, CapabilityProposal, GraduationReceipt as CapabilityGraduationReceipt, PracticeResult, ValidationEvidence, ValidationReceipt
from .autonomy_graduation import AutonomyEvidence, AutonomyGraduator, GraduationPolicy, GraduationReceipt, LEVELS
from .deep_evaluation import BenchmarkCase, DeepBenchmarkReport, DeepEvaluator

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
    "Observation", "WorldFact", "WorldPrediction", "PredictionError", "WorldModel", "BeliefEvidence", "Hypothesis", "HypothesisEngine",
    "ReasoningLedger", "ReasoningRecord", "CausalLink", "CausalModel", "CounterfactualEngine", "CounterfactualQuery", "CounterfactualResult",
    "Goal", "GoalManager", "InformationAction", "InformationPlan", "InformationPlanner", "CapabilityProfile", "SelfModel",
    "CapabilityCase", "CapabilityEvaluator", "CaseResult", "EvaluationReport", "KINDS", "CognitiveRuntime",
    "CognitiveEpisode", "CognitiveEpisodeReceipt", "CognitiveLoop", "CognitiveController", "CognitivePlan",
    "LearningExperience", "TransferCandidate", "ConsolidationReceipt", "LearningTransfer",
    "Abstraction", "AnalogyCandidate", "GeneralizationEngine", "SkillGraph", "SkillNode", "CuriosityEngine", "LearningChoice", "LearningNeed",
    "BenchmarkObservation", "RegressionResult", "ContinualLearningGuard",
    "CapabilityAcquirer", "CapabilityNeed", "CapabilityProposal", "PracticeResult", "CapabilityGraduationReceipt", "ValidationEvidence", "ValidationReceipt",
    "AutonomyEvidence", "AutonomyGraduator", "GraduationPolicy", "GraduationReceipt", "LEVELS",
    "BenchmarkCase", "DeepBenchmarkReport", "DeepEvaluator",
]
