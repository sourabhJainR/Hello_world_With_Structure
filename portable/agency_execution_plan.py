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
        )
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
    overlaps = (aw & bw) | (aw & br) | (bw & ar)
    return tuple(sorted(overlaps))


def detect_conflicts(work: Sequence[SpecialistWork]) -> tuple[PlanConflict, ...]:
    conflicts: list[PlanConflict] = []
    for i, left in enumerate(work):
        for right in work[i + 1 :]:
            paths = _overlap(left, right)
            if not paths:
                continue
            if left.mutation_mode == "read-only" and right.mutation_mode == "read-only":
                continue
            conflicts.append(
                PlanConflict(left.specialist, right.specialist, paths, "shared read/write resource")
            )
    return tuple(conflicts)


def build_plan(work: Sequence[SpecialistWork]) -> ExecutionPlan:
    """Build deterministic waves with dependency and mutation-conflict ordering."""
    items = tuple(sorted(work, key=lambda x: (-x.priority, x.role, x.specialist)))
    names = {item.specialist for item in items}
    blocked: set[str] = set()
    for item in items:
        unknown = sorted(set(item.depends_on) - names)
        if unknown:
            blocked.add(f"{item.specialist}: missing dependencies {','.join(unknown)}")

    conflicts = detect_conflicts(items)
    waves: list[list[str]] = []
    placed: dict[str, int] = {}
    conflict_pairs = {(c.left, c.right) for c in conflicts} | {(c.right, c.left) for c in conflicts}

    for item in items:
        earliest = 0
        if item.depends_on:
            earliest = max((placed[d] + 1 for d in item.depends_on if d in placed), default=0)
        while True:
            while len(waves) <= earliest:
                waves.append([])
            incompatible = False
            for other in waves[earliest]:
                if (item.specialist, other) in conflict_pairs:
                    incompatible = True
                    break
                if item.mutation_mode != "read-only" or next(x for x in items if x.specialist == other).mutation_mode != "read-only":
                    # Independent mutations are still serialized to keep mutation ordering explicit.
                    incompatible = True
                    break
            if not incompatible:
                break
            earliest += 1
        waves[earliest].append(item.specialist)
        placed[item.specialist] = earliest

    normalized = tuple(
        ExecutionWave(i, tuple(sorted(names_in_wave)), any(next(x for x in items if x.specialist == name).mutation_mode != "read-only" for name in names_in_wave))
        for i, names_in_wave in enumerate(waves)
        if names_in_wave
    )
    return ExecutionPlan(normalized, conflicts, tuple(sorted(blocked)))
