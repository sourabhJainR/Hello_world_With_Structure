"""Composite engineering quality gate."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class QualityGate:
    name: str
    passed: bool
    evidence_ids: tuple[str,...]=()
    defects: tuple[str,...]=()

@dataclass(frozen=True)
class QualityReport:
    gates: tuple[QualityGate,...]
    passed: bool
    blocking_defects: tuple[str,...]

class EngineeringQualityGate:
    def evaluate(self,gates:tuple[QualityGate,...])->QualityReport:
        if not gates: raise ValueError("at least one quality gate is required")
        defects=tuple(d for g in gates for d in g.defects)
        for g in gates:
            if g.passed and not g.evidence_ids: defects += (f"{g.name}: passed gate lacks evidence",)
        passed=all(g.passed and bool(g.evidence_ids) for g in gates) and not defects
        return QualityReport(gates,passed,defects)
    def from_scores(self,scores:Mapping[str,float],*,threshold:float=.8)->QualityReport:
        if not 0<=threshold<=1: raise ValueError("threshold must be 0..1")
        return self.evaluate(tuple(QualityGate(k,0<=v<=1 and v>=threshold,(f"score:{k}",),() if v>=threshold else (f"{k} below threshold",)) for k,v in sorted(scores.items())))

__all__=["QualityGate","QualityReport","EngineeringQualityGate"]
