"""Capability-aware, deterministic execution runtime for specialist agents."""
from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Callable, Mapping
from .agency_registry import rank
from .agency_quality import ReviewFinding, QualityReceipt, evaluate
from .agency_provenance import ProvenanceLedger

@dataclass(frozen=True)
class TaskProfile:
    task_id: str
    request: str
    artifact_type: str = "code"
    risk: str = "normal"
    mutation_mode: str = "bounded"
    acceptance: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.request.strip(): raise ValueError("task_id and request are required")
        if self.mutation_mode not in {"read-only", "bounded", "serialized"}: raise ValueError("unsupported mutation mode")

@dataclass(frozen=True)
class Assignment:
    specialist: str
    role: str
    score: int
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class EvidenceItem:
    source: str
    claim: str
    locator: str = ""
    confidence: str = "stated"

@dataclass(frozen=True)
class LedgerEntry:
    event: str
    detail: str
    evidence_ids: tuple[str, ...] = ()
    @property
    def event_id(self) -> str:
        return sha256(f"{self.event}|{self.detail}|{'|'.join(self.evidence_ids)}".encode()).hexdigest()[:16]

@dataclass
class ExecutionResult:
    task: TaskProfile
    assignments: list[Assignment]
    deliverables: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    findings: list[ReviewFinding] = field(default_factory=list)
    dimensions: dict[str, int] = field(default_factory=dict)
    hard_gates: dict[str, bool] = field(default_factory=dict)
    ledger: list[LedgerEntry] = field(default_factory=list)
    receipt: QualityReceipt | None = None
    def as_dict(self) -> dict:
        return {"task_id": self.task.task_id, "assignments":[a.__dict__ for a in self.assignments], "deliverables":self.deliverables, "evidence":[e.__dict__ for e in self.evidence], "verification":self.verification, "findings":[f.__dict__ for f in self.findings], "dimensions":self.dimensions, "hard_gates":self.hard_gates, "ledger":[{"event_id":e.event_id,"event":e.event,"detail":e.detail,"evidence_ids":e.evidence_ids} for e in self.ledger], "receipt":self.receipt.as_dict() if self.receipt else None}
    def provenance(self) -> ProvenanceLedger:
        ledger = ProvenanceLedger()
        for entry in self.ledger: ledger.append(self.task.task_id, entry.event, entry.detail, entry.evidence_ids)
        return ledger

def plan_task(task: TaskProfile, registry: Mapping[str, object] | None = None, support_limit: int = 2) -> list[Assignment]:
    if support_limit < 0: raise ValueError("support_limit must be non-negative")
    ranked = rank(task.request + " " + task.artifact_type + " " + " ".join(task.technologies), registry=registry, limit=max(3, support_limit + 1))
    if not ranked: return []
    assignments=[Assignment(str(ranked[0]["name"]),"primary",int(ranked[0]["score"]),tuple(ranked[0]["reasons"]))]
    for candidate in ranked[1:support_limit+1]:
        role="reviewer" if str(candidate.get("division","")).lower() in {"testing","security"} else "support"
        assignments.append(Assignment(str(candidate["name"]),role,int(candidate["score"]),tuple(candidate["reasons"])))
    return assignments

def evidence_id(item: EvidenceItem) -> str:
    return sha256(f"{item.source}|{item.claim}|{item.locator}".encode()).hexdigest()[:16]

def execute(task: TaskProfile, worker: Callable[[TaskProfile,list[Assignment]], Mapping[str,object]], registry: Mapping[str,object] | None = None, rubric: Mapping[str,object] | None = None, support_limit: int = 2) -> ExecutionResult:
    assignments=plan_task(task,registry=registry,support_limit=support_limit); result=ExecutionResult(task,assignments); result.ledger.append(LedgerEntry("planned",f"selected {len(assignments)} specialist(s)"))
    raw=dict(worker(task,assignments)); result.deliverables=[str(x) for x in raw.get("deliverables",())]; result.verification=[str(x) for x in raw.get("verification",())]; result.dimensions={str(k):int(v) for k,v in dict(raw.get("dimensions",{})).items()}; result.hard_gates={str(k):bool(v) for k,v in dict(raw.get("hard_gates",{})).items()}; result.findings=list(raw.get("findings",()))
    for item in raw.get("evidence",()):
        evidence=item if isinstance(item,EvidenceItem) else EvidenceItem(**item); result.evidence.append(evidence); result.ledger.append(LedgerEntry("evidence",evidence.claim,(evidence_id(evidence),)))
    result.ledger.append(LedgerEntry("verified","; ".join(result.verification))); result.receipt=evaluate(result.dimensions,result.hard_gates,result.findings,[e.claim for e in result.evidence],rubric=rubric); return result
