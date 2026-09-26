"""Dependency-safe implementation planning for engineering tasks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class WorkStep:
    step_id: str
    description: str
    depends_on: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()

@dataclass(frozen=True)
class ImplementationPlan:
    steps: tuple[WorkStep, ...]
    parallel_groups: tuple[tuple[str, ...], ...]

    @property
    def complete(self) -> bool:
        ids={s.step_id for s in self.steps}
        return bool(self.steps) and all(set(s.depends_on)<=ids and s.verification for s in self.steps)

class ImplementationPlanner:
    def build(self, steps: Sequence[WorkStep]) -> ImplementationPlan:
        items=tuple(steps)
        ids=[s.step_id.strip() for s in items]
        if not items or any(not x for x in ids) or len(ids)!=len(set(ids)): raise ValueError("steps need unique IDs")
        known=set(ids)
        for s in items:
            if s.step_id in s.depends_on or not set(s.depends_on)<=known: raise ValueError("invalid dependency graph")
            if not s.verification: raise ValueError(f"{s.step_id}: verification required")
        groups=[]
        done=set()
        remaining={s.step_id:s for s in items}
        while remaining:
            ready=tuple(sorted(k for k,s in remaining.items() if set(s.depends_on)<=done))
            if not ready: raise ValueError("dependency graph contains a cycle")
            groups.append(ready); done.update(ready)
            for k in ready: remaining.pop(k)
        return ImplementationPlan(items, tuple(groups))

__all__=["WorkStep","ImplementationPlan","ImplementationPlanner"]
