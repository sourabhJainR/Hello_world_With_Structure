"""Composition facade for AER's cognitive primitives.

This facade centralizes the semantic subsystems around one project key while
keeping StateGraph/Orchestrator as the execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agi_evaluation import CapabilityEvaluator
from .causal_model import CausalModel
from .context_graph import ContextGraph
from .goal_manager import GoalManager
from .hypothesis_engine import HypothesisEngine
from .information_planner import InformationPlanner
from .persistent_memory import PersistentMemory
from .reasoning_ledger import ReasoningLedger
from .self_model import SelfModel
from .world_model import WorldModel


@dataclass(frozen=True)
class CognitiveRuntime:
    """Project-scoped access to AER cognitive state and evaluation."""

    project: str
    memory: PersistentMemory
    graph: ContextGraph
    world: WorldModel
    hypotheses: HypothesisEngine
    reasoning: ReasoningLedger
    causal: CausalModel
    goals: GoalManager
    information: InformationPlanner
    self_model: SelfModel
    evaluator: CapabilityEvaluator

    @classmethod
    def create(cls, memory: PersistentMemory, project: str) -> "CognitiveRuntime":
        graph = ContextGraph(memory, project)
        return cls(project, memory, graph, WorldModel(memory, project), HypothesisEngine(memory, project),
                   ReasoningLedger(memory, project), CausalModel(graph), GoalManager(memory, project),
                   InformationPlanner(), SelfModel(memory, project), CapabilityEvaluator())

    def digest(self) -> str:
        """Return a compact digest of durable semantic state."""
        import hashlib
        parts = [self.graph.digest(), self.world.digest()]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


__all__ = ["CognitiveRuntime"]
