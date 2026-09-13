"""Deterministic conflict-aware multi-specialist execution planning.

Planning only: this module never executes commands, grants permissions, or mutates
repository state. Read-only work may share a wave; overlapping mutations are
serialized by resource conflict.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence


MUTATION_MODES = {"read-only", "bounded", "serialized"}
ROLES = {"primary", "support", "reviewer"}


@dataclass(frozen=True)
class SpecialistWork:
    specialist: str
    role: str
    mutation_mode: str = "read-only"
    read_paths: tuple[str, ...] = ()
    write_paths: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.specialist.strip():
            raise ValueError("specialist is required")
        if self.role not in ROLES:
            raise ValueError("unsupported specialist role")
        if self.mutation_mode not in MUTATION_MODES:
            raise ValueError("unsupported mutation mode")
        if self.mutation_mode == "read-only" and self.write_paths:
            raise ValueError("read-only work cannot declare write paths")
        if self.mutation_mode != "read-only" and not self.write_paths:
            raise ValueError("mutating work must declare write paths")


@dataclass(frozen=True)
class PlanConflict:
    left: str
    right: str
    paths: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ExecutionWave:
    index: int
    specialists: tuple[str, ...]
    mutation: bool


@dataclass(frozen=True)
class ExecutionPlan:
    waves: tuple[ExecutionWave, ...]
    conflicts: tuple[PlanConflict, ...]
    blocked: tuple[str, ...] = ()

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def digest(self) -> str:
        payload = "|".join(
            f"{w.index}:{','.join(w.specialists)}:{int(w.mutation)}" for w in self.waves
        ) + "#" + "|".join(
            f"{c.left}:{c.right}:{','.join(c.paths)}:{c.reason}" for c in self.conflicts
        ) + "#" + "|".join(self.blocked)
        return sha256(payload.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict[str, object]:
        return {
            "waves": [
                {"index": w.index, "specialists": list(w.specialists), "mutation": w.mutation}
                for w in self.waves
            ],
            "conflicts": [c.__dict__ for c in self.conflicts],
            "blocked": list(self.blocked),
            "digest": self.digest(),
        }


def _norm(paths: Iterable[str]) -> set[str]:
    return {str(p).strip().rstrip("/") for p in paths if str(p).strip()}


def _overlap(a: SpecialistWork, b: SpecialistWork) -> tuple[str, ...]:
    aw, bw = _norm(a.write_paths), _norm(b.write_paths)
    ar, br = _norm(a.read_paths), _norm(b.read_paths)
    return tuple(sorted((aw & bw) | (aw & br) | (bw & ar)))


def detect_conflicts(work: Sequence[SpecialistWork]) -> tuple[PlanConflict, ...]:
    conflicts: list[PlanConflict] = []
    for i, left in enumerate(work):
        for right in work[i + 1 :]:
            paths = _overlap(left, right)
            if not paths or (left.mutation_mode == "read-only" and right.mutation_mode == "read-only"):
                continue
            conflicts.append(PlanConflict(left.specialist, right.specialist, paths, "shared read/write resource"))
    return tuple(conflicts)


def _dependency_order(items: Sequence[SpecialistWork]) -> tuple[list[SpecialistWork], set[str], set[str]]:
    by_name = {item.specialist: item for item in items}
    missing: set[str] = set()
    for item in items:
        missing.update(d for d in item.depends_on if d not in by_name)
    blocked = {
        f"{item.specialist}: missing dependencies {','.join(sorted(set(item.depends_on) - by_name.keys()))}"
        for item in items
        if set(item.depends_on) - by_name.keys()
    }

    indegree = {name: 0 for name in by_name}
    children: dict[str, set[str]] = {name: set() for name in by_name}
    for item in items:
        for dependency in set(item.depends_on) & by_name.keys():
            indegree[item.specialist] += 1
            children[dependency].add(item.specialist)

    ready = sorted((name for name, degree in indegree.items() if degree == 0), key=lambda n: (-by_name[n].priority, by_name[n].role, n))
    ordered: list[SpecialistWork] = []
    while ready:
        name = ready.pop(0)
        ordered.append(by_name[name])
        for child in sorted(children[name], key=lambda n: (-by_name[n].priority, by_name[n].role, n)):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
        ready.sort(key=lambda n: (-by_name[n].priority, by_name[n].role, n))

    cycle_nodes = set(by_name) - {item.specialist for item in ordered}
    blocked.update(f"{name}: dependency cycle" for name in sorted(cycle_nodes))
    return ordered, blocked, missing


def build_plan(work: Sequence[SpecialistWork]) -> ExecutionPlan:
    """Build deterministic waves with dependency-first ordering and serialized mutations."""
    if not work:
        return ExecutionPlan((), ())
    items = tuple(work)
    names = {item.specialist for item in items}
    if len(names) != len(items):
        raise ValueError("specialist names must be unique")

    ordered, blocked, _missing = _dependency_order(items)
    conflicts = detect_conflicts(ordered)
    conflict_pairs = {(c.left, c.right) for c in conflicts} | {(c.right, c.left) for c in conflicts}
    work_by_name = {item.specialist: item for item in ordered}

    waves: list[list[str]] = []
    placed: dict[str, int] = {}
    for item in ordered:
        if item.specialist in {b.split(":", 1)[0] for b in blocked}:
            continue
        earliest = max((placed[d] + 1 for d in item.depends_on if d in placed), default=0)
        while True:
            while len(waves) <= earliest:
                waves.append([])
            incompatible = False
            for other in waves[earliest]:
                other_item = work_by_name[other]
                if (item.specialist, other) in conflict_pairs:
                    incompatible = True
                    break
                if item.mutation_mode != "read-only" or other_item.mutation_mode != "read-only":
                    incompatible = True
                    break
            if not incompatible:
                break
            earliest += 1
        waves[earliest].append(item.specialist)
        placed[item.specialist] = earliest

    normalized = tuple(
        ExecutionWave(
            i,
            tuple(sorted(names_in_wave)),
            any(work_by_name[name].mutation_mode != "read-only" for name in names_in_wave),
        )
        for i, names_in_wave in enumerate(waves)
        if names_in_wave
    )
    return ExecutionPlan(normalized, conflicts, tuple(sorted(blocked)))
