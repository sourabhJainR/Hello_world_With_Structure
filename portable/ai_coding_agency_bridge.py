"""Bridge the AI coding orchestrator contract to the Agency Runtime.

This module is intentionally provider-neutral. The host orchestrator owns model/tool
execution, permissions, concurrency and side effects; this bridge owns task profiling,
specialist planning, evidence, provenance and release gating.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .agency_artifact_regression import ArtifactSnapshot, RegressionDecision, compare_artifacts
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
    protected_paths: tuple[str, ...] = ()
    allowed_artifact_changes: tuple[str, ...] = ()


@dataclass
class OrchestratorRun:
    task: CodingTask
    execution: ExecutionResult
    regression: RegressionDecision | None
    release: ReleaseDecision
    provenance: ProvenanceLedger

    @property
    def ready(self) -> bool:
        return self.release.releasable

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task.task_id,
            "execution": self.execution.as_dict(),
            "regression": self.regression.as_dict() if self.regression else None,
            "release": self.release.as_dict(),
            "provenance": self.provenance.as_dict(),
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
    registry: Mapping[str, object] | None = None,
    rubric: Mapping[str, object] | None = None,
) -> OrchestratorRun:
    """Execute a coding task through Agency controls without owning host side effects."""
    profile = TaskProfile(
        task_id=task.task_id,
        request=task.goal,
        artifact_type="code",
        risk=task.risk,
        mutation_mode=task.mutation_mode,
        acceptance=task.acceptance,
        technologies=task.technologies,
    )
    execution = execute(profile, worker, registry=registry, rubric=rubric)
    provenance = ProvenanceLedger()
    provenance.append(task.task_id, "task-profiled", task.goal)
    provenance.append(task.task_id, "specialists-planned", ",".join(a.specialist for a in execution.assignments))
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
        release = decide_release(0, 90, {}, regression_status=regression_status)
    else:
        release = decide_release(
            receipt.score,
            receipt.threshold,
            receipt.hard_gates,
            receipt.findings,
            regression_status=regression_status,
        )
    provenance.append(task.task_id, "release-decision", release.status)
    return OrchestratorRun(task, execution, regression, release, provenance)


def verify_provenance(run: OrchestratorRun) -> None:
    """Fail closed if the run trace is structurally or cryptographically invalid."""
    run.provenance.verify()
