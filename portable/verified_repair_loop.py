"""Bounded autonomous repair planning with regression protection."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Sequence

@dataclass(frozen=True)
class RepairAttempt:
    attempt: int
    defect: str
    score: float
    verified: bool
    evidence_id: str

@dataclass(frozen=True)
class RepairReport:
    attempts: tuple[RepairAttempt,...]
    accepted: bool
    final_score: float

class VerifiedRepairLoop:
    def run(self, defect:str, baseline:float, repair:Callable[[str,int],RepairAttempt], *, max_attempts:int=3, minimum_improvement:float=.01)->RepairReport:
        if not defect.strip() or max_attempts<1: raise ValueError("defect and positive attempt bound are required")
        attempts=[]; best=baseline
        for i in range(1,max_attempts+1):
            a=repair(defect,i)
            if a.attempt!=i or not a.evidence_id: raise ValueError("repair attempt identity/evidence invalid")
            if not 0<=a.score<=1: raise ValueError("repair score must be 0..1")
            attempts.append(a)
            if a.verified and a.score>best: best=a.score
            if a.verified and a.score>=baseline+minimum_improvement: return RepairReport(tuple(attempts),True,a.score)
        return RepairReport(tuple(attempts),False,best)

__all__=["RepairAttempt","RepairReport","VerifiedRepairLoop"]
