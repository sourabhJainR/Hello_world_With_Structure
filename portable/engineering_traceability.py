"""Requirement-to-evidence traceability and completeness checking."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class TraceLink:
    requirement_id: str
    implementation_ids: tuple[str,...]
    test_ids: tuple[str,...]
    evidence_ids: tuple[str,...]

@dataclass(frozen=True)
class TraceabilityReport:
    links: tuple[TraceLink,...]
    missing: tuple[str,...]
    completeness: float
    verified: bool

class EngineeringTraceability:
    def evaluate(self,links:Sequence[TraceLink],required_requirements:Sequence[str])->TraceabilityReport:
        items=tuple(links); required=tuple(dict.fromkeys(x.strip() for x in required_requirements if x.strip()))
        by={x.requirement_id:x for x in items}
        missing=[]
        for rid in required:
            x=by.get(rid)
            if x is None or not x.implementation_ids or not x.test_ids or not x.evidence_ids: missing.append(rid)
        completeness=0.0 if not required else (len(required)-len(missing))/len(required)
        return TraceabilityReport(items,tuple(missing),completeness,not missing)
__all__=["TraceLink","TraceabilityReport","EngineeringTraceability"]
