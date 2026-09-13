"""Convert Agency specialist assignments into a conflict-aware execution plan."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .agency_execution_plan import ExecutionPlan, SpecialistWork, build_plan
from .agency_runtime import Assignment


@dataclass(frozen=True)
class SpecialistResourceProfile:
    specialist: str
    read_paths: tuple[str, ...] = ()
    write_paths: tuple[str, ...] = ()
    mutation_mode: str = "read-only"
    depends_on: tuple[str, ...] = ()
    priority: int = 0


def build_specialist_plan(
    assignments: Iterable[Assignment],
    resources: Mapping[str, SpecialistResourceProfile] | None = None,
) -> ExecutionPlan:
    """Plan assigned specialists while preserving deterministic role ordering."""
    resources = resources or {}
    work: list[SpecialistWork] = []
    for assignment in assignments:
        profile = resources.get(assignment.specialist, SpecialistResourceProfile(assignment.specialist))
        work.append(
            SpecialistWork(
                specialist=assignment.specialist,
                role=assignment.role,
                mutation_mode=profile.mutation_mode,
                read_paths=profile.read_paths,
                write_paths=profile.write_paths,
                depends_on=profile.depends_on,
                priority=profile.priority,
            )
        )
    return build_plan(work)
