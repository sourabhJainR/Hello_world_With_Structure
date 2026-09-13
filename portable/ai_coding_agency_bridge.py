"""Bridge the AI coding orchestrator contract to the Agency Runtime.

The host orchestrator owns model/tool execution, permissions, concurrency and side
effects. Agency Runtime owns task profiling, specialist selection, scheduling,
evidence, provenance, regression, adaptive feedback and release gating.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Iterable, Mapping

from .agency_adaptive_planning import (
    AdaptiveRecommendation,
    BenchmarkHistory,
    apply_recommendation,
    observe_run,
    recommend_plan,
)
from .agency_artifact_regression import ArtifactSnapshot, RegressionDecision, compare_artifacts
from .agency_multi_specialist import SpecialistResourceProfile, build_specialist_plan
from .agency_provenance import ProvenanceLedger
from .agency_release import ReleaseDecision, decide_release
from .agency_runtime import Assignment, ExecutionResult, TaskProfile, execute


@dataclass(frozen=True)
class CodingTask:
    task_id: str
    goal: str
    acceptance: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()
    risk: str = "normal"
    mutation_mode: str = "bounded"
    support_limit: int = 2
    protected_paths: tuple[str, ...] = ()
    allowed_artifact_changes: tuple[str, ...] = ()


@dataclass
class OrchestratorRun:
    task: CodingTask
    execution: ExecutionResult
    execution_plan: object
    regression: RegressionDecision | None
    release: ReleaseDecision
    provenance: ProvenanceLedger
    adaptive_recommendation: AdaptiveRecommendation | None = None
    benchmark: object | None = None

    @property
    def ready(self) -> bool:
        return self.release.releasable

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task.task_id,
            "execution": self.execution.as_dict(),
            "execution_plan": self.execution_plan.as_dict(),
            "regression": self.regression.as_dict() if self.regression else None,
            "release": self.release.as_dict(),
            "provenance": self.provenance.as_dict(),
            "adaptive_recommendation": self.adaptive_recommendation.as_dict() if self.adaptive_recommendation else None,
            "benchmark": self.benchmark.as_dict() if self.benchmark else None,
            "ready": self.ready,
        }


def _artifact_map(items: Iterable[ArtifactSnapshot]) -> dict[str, ArtifactSnapshot]:
    return {item.path: item for item in items}


def run_coding_task(
    task: CodingTask,
    worker: Callable[[TaskProfile, list[Assignment]], Mapping[str, object]],
    *,
    baseline_artifacts: Iterable[ArtifactSnapshot] = (),
    current_artifacts: Iterable[ArtifactSnapshot] = (),
    resource_profiles: Mapping[str, SpecialistResourceProfile] | None = None,
    benchmark_history: BenchmarkHistory | Iterable = (),
    registry: Mapping[str, object] | None = None,
    rubric: Mapping[str, object] | None = None,
) -> OrchestratorRun:
    """Execute a task with v10 adaptation from prior benchmark outcomes.

    Historical outcomes shape the next task's mutation posture and specialist
    count, but never expand host permissions or bypass the v9 execution plan.
    """
    history = benchmark_history if isinstance(benchmark_history, BenchmarkHistory) else BenchmarkHistory(list(benchmark_history))
    recommendation = recommend_plan(
        history,
        requested_mutation_mode=task.mutation_mode,
        requested_support_limit=task.support_limit,
    )
    mutation_mode, support_limit = apply_recommendation(
        task.mutation_mode,
        task.support_limit,
        recommendation,
    )
    effective_task = replace(task, mutation_mode=mutation_mode, support_limit=support_limit)
    profile = TaskProfile(
        task_id=effective_task.task_id,
        request=effective_task.goal,
        artifact_type="code",
        risk=effective_task.risk,
        mutation_mode=effective_task.mutation_mode,
        acceptance=effective_task.acceptance,
        technologies=effective_task.technologies,
    )
    execution = execute(profile, worker, registry=registry, rubric=rubric, support_limit=effective_task.support_limit)
    execution_plan = build_specialist_plan(execution.assignments, resource_profiles)
    provenance = ProvenanceLedger()
    provenance.append(task.task_id, "task-profiled", task.goal)
    provenance.append(task.task_id, "adaptive-recommendation", str(recommendation.as_dict()))
    provenance.append(task.task_id, "specialists-planned", ",".join(a.specialist for a in execution.assignments))
    provenance.append(task.task_id, "execution-plan", execution_plan.digest())
    for item in execution.evidence:
        provenance.append(task.task_id, "evidence-recorded", item.claim)
    provenance.append(task.task_id, "verification-recorded", ";".join(execution.verification))

    regression: RegressionDecision | None = None
    regression_status: str | None = None
    if baseline_artifacts or current_artifacts:
        regression = compare_artifacts(
            _artifact_map(baseline_artifacts),
            _artifact_map(current_artifacts),
            allowed_changes=task.allowed_artifact_changes,
        )
        regression_status = regression.status
        provenance.append(task.task_id, "artifact-regression", regression.status)

    receipt = execution.receipt
    if receipt is None:
        release = decide_release(0, 90, {}, {}, regression_status=regression_status)
    else:
        release = decide_release(
            receipt.score,
            receipt.threshold,
            receipt.hard_gates,
            receipt.findings,
            regression_status=regression_status,
        )
    provenance.append(task.task_id, "release-decision", release.status)
    benchmark = observe_run(
        task_id=task.task_id,
        plan=execution_plan,
        provenance=provenance,
        release_status=release.status,
        regression_status=regression_status,
        quality_score=receipt.score if receipt else 0,
        specialist_results=tuple(f"{a.specialist}:{a.role}" for a in execution.assignments),
    )
    provenance.append(task.task_id, "benchmark-observed", benchmark.plan_digest, (benchmark.plan_digest,))
    history.add(benchmark)
    return OrchestratorRun(task, execution, execution_plan, regression, release, provenance, recommendation, benchmark)


def verify_provenance(run: OrchestratorRun) -> None:
    """Fail closed if the persisted run trace is structurally or cryptographically invalid."""
    run.provenance.verify()
