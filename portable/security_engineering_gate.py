"""Threat-model and security acceptance gate for autonomous engineering."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Threat:
    threat_id: str
    boundary: str
    scenario: str
    mitigation: str
    verified: bool=False

@dataclass(frozen=True)
class SecurityReport:
    threats: tuple[Threat,...]
    passed: bool
    unresolved: tuple[str,...]

class SecurityEngineeringGate:
    def assess(self, threats:Sequence[Threat])->SecurityReport:
        items=tuple(threats)
        if not items: raise ValueError("threat model cannot be empty")
        unresolved=tuple(t.threat_id for t in items if not t.boundary or not t.scenario or not t.mitigation or not t.verified)
        return SecurityReport(items,not unresolved,unresolved)
    def require_boundaries(self, boundaries:Sequence[str], threats:Sequence[Threat])->tuple[str,...]:
        known={x.strip() for x in boundaries if x.strip()}
        return tuple(b for b in sorted({t.boundary for t in threats}) if b not in known)

__all__=["Threat","SecurityReport","SecurityEngineeringGate"]
