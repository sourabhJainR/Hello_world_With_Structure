"""Model/topology-neutral benchmark harness for engineering competence."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Sequence

@dataclass(frozen=True)
class ModelEvaluation:
    model: str
    task_id: str
    score: float
    verified: bool
    evidence_id: str

@dataclass(frozen=True)
class ModelBenchmarkReport:
    evaluations: tuple[ModelEvaluation,...]
    coverage: dict[str,float]
    verified: bool

class ModelTopologyBenchmark:
    """Compare systems on identical tasks without baking in a preferred topology."""
    def run(self, models:Sequence[str], task_ids:Sequence[str], evaluator:Callable[[str,str],ModelEvaluation])->ModelBenchmarkReport:
        ms=tuple(dict.fromkeys(x.strip() for x in models if x.strip())); ts=tuple(dict.fromkeys(x.strip() for x in task_ids if x.strip()))
        if not ms or not ts: raise ValueError("models and tasks are required")
        out=[]
        for model in ms:
            for task in ts:
                result=evaluator(model,task)
                if result.model!=model or result.task_id!=task: raise ValueError("evaluation identity mismatch")
                if not 0<=result.score<=1: raise ValueError("score must be 0..1")
                if result.verified and not result.evidence_id: raise ValueError("verified result needs evidence")
                out.append(result)
        coverage={m:sum(x.score for x in out if x.model==m)/len(ts) for m in ms}
        return ModelBenchmarkReport(tuple(out),coverage,all(x.verified and x.evidence_id for x in out))

__all__=["ModelEvaluation","ModelBenchmarkReport","ModelTopologyBenchmark"]
