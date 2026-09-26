"""World Mega Model control plane for AER.

This is a bounded, evidence-first world-model facade: it unifies durable
world state, beliefs, goals, causal reasoning, self-calibration, pathway
discovery, capability evolution, transfer, and regression gating.

It is not a claim of AGI or a single neural model. The goal is a reusable
architecture for increasingly general autonomous problem solving while the
execution runtime and safety limits remain authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from .agency_regression_loop import PromotionDecision, PromotionPolicy
from .capability_acquisition import CapabilityAcquirer, CapabilityProposal
from .capability_evolution import CapabilityEvolution, CapabilityEvolutionDecision
from .cognitive_controller import CognitiveController, CognitivePlan
from .cognitive_runtime import CognitiveRuntime
from .continual_learning import BenchmarkObservation, ContinualLearningGuard, RegressionResult
from .execution_strategy import ExecutionPathway, PathwayOptimizer, ExecutionStrategy, execution_strategy
from .generalization import Abstraction, AnalogyCandidate, GeneralizationEngine
from .learning_transfer import LearningExperience, LearningTransfer, TransferCandidate
from .persistent_memory import PersistentMemory
from .transfer_validation import TransferValidation, TransferValidationReceipt, TransferValidator
from .world_model import Observation, PredictionError, WorldModel, WorldPrediction


@dataclass(frozen=True)
class MegaPlan:
    """Bounded cognitive plan plus a candidate execution pathway."""

    cognitive: CognitivePlan
    pathway: ExecutionPathway | None
    strategy: str


@dataclass(frozen=True)
class EvolutionReceipt:
    """Immutable decision record for a proposed self-improvement."""

    status: str
    capability: str
    proposal_id: str | None
    pathway: ExecutionPathway | None
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "capability": self.capability,
            "proposal_id": self.proposal_id,
            "pathway": {
                "capability": self.pathway.capability,
                "resource_lane": self.pathway.resource_lane,
                "verification_depth": self.pathway.verification_depth,
                "retry_action": self.pathway.retry_action,
                "score": self.pathway.score,
                "confidence": self.pathway.confidence,
            } if self.pathway else None,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class MegaPromotion:
    """Promotion gate result for a candidate capability or pathway."""

    accepted: bool
    action: str
    reasons: tuple[str, ...]
    regression: RegressionResult | None = None


class WorldMegaModel:
    """Project-scoped world-and-self model with bounded self-evolution.

    The facade composes existing AER primitives rather than replacing them.
    It can observe the world, reason about uncertainty, discover pathways,
    detect repeated capability gaps, validate transfer, and gate promotion.
    It never directly grants execution authority to learned content.
    """

    def __init__(
        self,
        memory: PersistentMemory,
        project: str,
        *,
        experience_router=None,
        min_failures: int = 3,
        min_evidence: int = 3,
    ) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        self.memory = memory
        self.project = project.strip()
        self.cognitive = CognitiveRuntime.create(memory, self.project)
        self.controller = CognitiveController(self.cognitive)
        self.world: WorldModel = self.cognitive.world
        self.acquirer = CapabilityAcquirer(memory, self.project, min_missing=min_failures)
        self.capability_evolution = CapabilityEvolution(
            self.acquirer,
            min_failures=min_failures,
            min_independent_evidence=min_evidence,
        )
        self.generalization = GeneralizationEngine(memory, self.project)
        self.transfer = LearningTransfer(memory, self.project)
        self.transfer_validator = TransferValidator(self.transfer)
        self.continual = ContinualLearningGuard(memory, self.project)
        self.experience_router = experience_router
        self.pathways = PathwayOptimizer(experience_router) if experience_router is not None else None

    def observe(self, observation: Observation) -> Observation:
        return self.world.observe(observation)

    def plan(
        self,
        intent: str,
        *,
        capability: str | None = None,
        uncertainty: float = 0.5,
        entity_id: str | None = None,
        predicate: str | None = None,
        action: str | None = None,
        current_value: object | None = None,
        strategy: str = "default",
        capabilities: Sequence[str] = (),
    ) -> MegaPlan:
        cognitive = self.controller.plan(
            intent,
            capability=capability,
            uncertainty=uncertainty,
            entity_id=entity_id,
            predicate=predicate,
            action=action,
            current_value=current_value,
        )
        pathway = None
        if self.pathways is not None and capabilities:
            selected = tuple(dict.fromkeys(str(item).strip() for item in capabilities if str(item).strip()))
            if selected:
                profile = execution_strategy(strategy)
                pathway = self.pathways.discover(
                    capabilities=selected,
                    key_prefix=f"{self.project}:{intent.strip()}",
                    strategy=profile,
                    risk=min(1.0, max(0.0, uncertainty)),
                    evidence_quality=max(0.0, min(1.0, 1.0 - uncertainty)),
                )
        return MegaPlan(cognitive, pathway, execution_strategy(strategy).name)

    def predict(self, entity_id: str, predicate: str, action: str, *, current_value: object | None = None) -> WorldPrediction | None:
        return self.world.predict_next(entity_id, predicate, action, current_value=current_value)

    def score_prediction(self, prediction: WorldPrediction, actual_value: object) -> PredictionError:
        return self.world.score_prediction(prediction, actual_value)

    def detect_capability_gap(
        self,
        task_family: str,
        capability: str,
        experiences: Iterable[Mapping[str, object]],
    ) -> CapabilityEvolutionDecision:
        return self.capability_evolution.evaluate(task_family, capability, experiences)

    def discover_pathway(
        self,
        *,
        capabilities: Sequence[str],
        key_prefix: str,
        strategy: str = "default",
        risk: float = 0.5,
        evidence_quality: float = 0.5,
        resource_lanes: Sequence[str] = ("agent", "local"),
    ) -> ExecutionPathway:
        if self.pathways is None:
            raise RuntimeError("discover_pathway requires an ExperienceRouter")
        profile = execution_strategy(strategy)
        return self.pathways.discover(
            capabilities=capabilities,
            key_prefix=key_prefix,
            strategy=profile,
            risk=risk,
            evidence_quality=evidence_quality,
            resource_lanes=resource_lanes,
        )

    def propose_evolution(
        self,
        task_family: str,
        capability: str,
        experiences: Iterable[Mapping[str, object]],
        *,
        capabilities: Sequence[str] = (),
        strategy: str = "default",
        risk: float = 0.5,
        evidence_quality: float = 0.5,
    ) -> EvolutionReceipt:
        decision = self.detect_capability_gap(task_family, capability, experiences)
        pathway = None
        if self.pathways is not None and capabilities:
            pathway = self.discover_pathway(
                capabilities=capabilities,
                key_prefix=f"{self.project}:{task_family}",
                strategy=strategy,
                risk=risk,
                evidence_quality=evidence_quality,
            )
        if decision.status != "propose":
            return EvolutionReceipt(
                decision.status,
                capability,
                None,
                pathway,
                decision.reasons,
            )
        proposal = decision.proposal
        return EvolutionReceipt(
            "proposed",
            capability,
            proposal.id if proposal else None,
            pathway,
            decision.reasons,
        )

    def validate_transfer(
        self,
        candidate: TransferCandidate,
        runner: Callable[[], TransferValidation],
        *,
        min_evidence: int = 1,
    ) -> TransferValidationReceipt:
        return self.transfer_validator.validate(candidate, runner, min_evidence=min_evidence)

    def record_abstraction(self, abstraction: Abstraction) -> None:
        self.generalization.record(abstraction)

    def analogies(
        self,
        structure: Iterable[str],
        *,
        target_conditions: Iterable[str] = (),
        min_similarity: float = 0.0,
        limit: int = 10,
    ) -> list[AnalogyCandidate]:
        return self.generalization.find_analogies(
            structure,
            target_conditions=target_conditions,
            min_similarity=min_similarity,
            limit=limit,
        )

    def record_learning(self, experience: LearningExperience) -> None:
        self.transfer.record(experience)

    def transfer_candidates(self, task_family: str, capability: str, *, limit: int = 10) -> list[TransferCandidate]:
        return self.transfer.transfer(task_family, capability, limit=limit)

    def gate_promotion(
        self,
        observation: BenchmarkObservation,
        *,
        policy: PromotionPolicy | None = None,
    ) -> MegaPromotion:
        """Require verified evidence and reject a candidate that regresses its baseline."""
        policy = policy or PromotionPolicy()
        regression = self.continual.compare(observation)
        if not observation.verified or not observation.evidence_ids:
            return MegaPromotion(False, "reject", ("verified benchmark evidence is required",), regression)
        if not regression.passed:
            return MegaPromotion(False, "reject", ("continual-learning regression gate failed",), regression)
        if observation.score < policy.quality_threshold:
            return MegaPromotion(
                False,
                "reject",
                ("candidate score is below promotion quality threshold",),
                regression,
            )
        return MegaPromotion(True, "promote", ("regression and quality gates passed",), regression)


__all__ = [
    "EvolutionReceipt",
    "MegaPlan",
    "MegaPromotion",
    "WorldMegaModel",
]
