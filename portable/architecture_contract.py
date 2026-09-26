"""Architecture contracts for requirements-driven engineering."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class ArchitectureComponent:
    name: str
    responsibility: str
    dependencies: tuple[str, ...] = ()
    interfaces: tuple[str, ...] = ()

@dataclass(frozen=True)
class ArchitectureContract:
    requirement_ids: tuple[str, ...]
    components: tuple[ArchitectureComponent, ...]
    boundaries: tuple[str, ...]
    risks: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return bool(self.requirement_ids and self.components and self.boundaries and self.verification)

class ArchitectureContractEngine:
    def build(self, requirement_ids: Sequence[str], components: Sequence[ArchitectureComponent], *, boundaries: Sequence[str], risks: Sequence[str]=(), verification: Sequence[str]=()) -> ArchitectureContract:
        req=tuple(dict.fromkeys(x.strip() for x in requirement_ids if x.strip()))
        comps=tuple(components)
        bounds=tuple(x.strip() for x in boundaries if x.strip())
        if not req or not comps or not bounds or not tuple(verification):
            raise ValueError("requirements, components, boundaries and verification are required")
        names=[c.name.strip() for c in comps]
        if any(not n for n in names) or len(names)!=len(set(names)): raise ValueError("component names must be unique")
        return ArchitectureContract(req, comps, bounds, tuple(risks), tuple(verification))
    def validate(self, contract: ArchitectureContract) -> tuple[str,...]:
        issues=[]
        if not contract.complete: issues.append("architecture contract is incomplete")
        known={c.name for c in contract.components}
        for c in contract.components:
            missing=[d for d in c.dependencies if d not in known]
            if missing: issues.append(f"{c.name}: unknown dependencies {missing}")
            if not c.interfaces: issues.append(f"{c.name}: interface contract missing")
        return tuple(issues)

__all__=["ArchitectureComponent","ArchitectureContract","ArchitectureContractEngine"]
