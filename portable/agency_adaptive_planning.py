"""Evidence-driven adaptive planning with single-agent-first execution."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable, Sequence

from .agency_execution_plan import ExecutionPlan
from .agency_provenance import ProvenanceLedger

MUTATION_ORDER = ("read-only", "bounded", "serialized")
EXECUTION_ORDER = ("single-agent", "multi-agent")


@dataclass(frozen=True)
class BenchmarkObservation:
    task_id: str
    plan_digest: str
    provenance_head: str
    release_status: str
    regression_status: str
    quality_score: int
    wave_count: int
    conflict_count: int
    blocked_count: int
    specialist_results: tuple[str, ...] = ()
    execution_mode: str = "single-agent"
    task_class: str = "general"
    model_id: str = "unknown"
    context_items: int = 0
    latency_ms: int = 0
    token_cost: int = 0
    human_corrections: int = 0
    rework_count: int = 0
    verification_failures: int = 0

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.plan_digest.strip():
            raise ValueError("task_id and plan_digest are required")
        if self.release_status not in {"passed", "failed", "blocked"}:
            raise ValueError("unsupported release status")
        if self.regression_status not in {"passed", "failed", "omitted"}:
            raise ValueError("unsupported regression status")
        if self.execution_mode not in EXECUTION_ORDER:
            raise ValueError("unsupported execution mode")
        if self.quality_score < 0:
            raise ValueError("quality_score cannot be negative")
        numeric = (self.wave_count, self.conflict_count, self.blocked_count, self.context_items, self.latency_ms, self.token_cost, self.human_corrections, self.rework_count, self.verification_failures)
        if any(value < 0 for value in numeric):
            raise ValueError("benchmark counts and costs cannot be negative")

    @property
    def passed(self) -> bool:
        return self.release_status == "passed" and self.regression_status != "failed" and self.verification_failures == 0

    @property
    def comparable_key(self) -> tuple[str, str]:
        return self.task_class, self.model_id

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "plan_digest": self.plan_digest,
            "provenance_head": self.provenance_head,
            "release_status": self.release_status,
            "regression_status": self.regression_status,
            "quality_score": self.quality_score,
            "wave_count": self.wave_count,
            "conflict_count": self.conflict_count,
            "blocked_count": self.blocked_count,
            "specialist_results": list(self.specialist_results),
            "execution_mode": self.execution_mode,
            "task_class": self.task_class,
            "model_id": self.model_id,
            "context_items": self.context_items,
            "latency_ms": self.latency_ms,
            "token_cost": self.token_cost,
            "human_corrections": self.human_corrections,
            "rework_count": self.rework_count,
            "verification_failures": self.verification_failures,
        }


@dataclass
class BenchmarkHistory:
    observations: list[BenchmarkObservation] = field(default_factory=list)

    def add(self, observation: BenchmarkObservation) -> None:
        self.observations.append(observation)

    def extend(self, observations: Iterable[BenchmarkObservation]) -> None:
        for observation in observations:
            self.add(observation)

    def as_dict(self) -> dict[str, object]:
        return {"observations": [item.as_dict() for item in self.observations]}

    def to_jsonl(self) -> str:
        return "".join(json.dumps(item.as_dict(), sort_keys=True) + "\n" for item in self.observations)

    @classmethod
    def from_jsonl(cls, text: str) -> "BenchmarkHistory":
        history = cls()
        for line in text.splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            history.add(BenchmarkObservation(
                str(data["task_id"]), str(data["plan_digest"]), str(data.get("provenance_head", "")),
                str(data["release_status"]), str(data["regression_status"]), int(data["quality_score"]),
                int(data["wave_count"]), int(data["conflict_count"]), int(data["blocked_count"]),
                tuple(str(x) for x in data.get("specialist_results", ())), str(data.get("execution_mode", "single-agent")),
                str(data.get("task_class", "general")), str(data.get("model_id", "unknown")),
                int(data.get("context_items", 0)), int(data.get("latency_ms", 0)), int(data.get("token_cost", 0)),
                int(data.get("human_corrections", 0)), int(data.get("rework_count", 0)), int(data.get("verification_failures", 0)),
            ))
        return history

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.to_jsonl(), encoding="utf-8")

    @classmethod
    def read(cls, path: str | Path) -> "BenchmarkHistory":
        return cls.from_jsonl(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class AdaptiveRecommendation:
    mutation_mode: str
    support_limit: int
    reasons: tuple[str, ...]
    confidence: str
    execution_mode: str = "single-agent"
    sample_count: int = 0
    comparable_sample_count: int = 0

    def __post_init__(self) -> None:
        if self.mutation_mode not in MUTATION_ORDER or self.execution_mode not in EXECUTION_ORDER:
            raise ValueError("unsupported recommendation mode")
        if self.support_limit < 0 or self.sample_count < 0 or self.comparable_sample_count < 0:
            raise ValueError("recommendation counts cannot be negative")
        if self.confidence not in {"none", "low", "medium", "high"}:
            raise ValueError("unsupported confidence")

    def as_dict(self) -> dict[str, object]:
        return {
            "mutation_mode": self.mutation_mode,
            "support_limit": self.support_limit,
            "reasons": list(self.reasons),
            "confidence": self.confidence,
            "execution_mode": self.execution_mode,
            "sample_count": self.sample_count,
            "comparable_sample_count": self.comparable_sample_count,
        }


def provenance_head(ledger: ProvenanceLedger) -> str:
    ledger.verify()
    return ledger.records[-1].record_hash if ledger.records else ""


def observe_run(*, task_id: str, plan: ExecutionPlan, provenance: ProvenanceLedger, release_status: str, regression_status: str | None, quality_score: int, specialist_results: Sequence[str] = (), execution_mode: str = "single-agent", task_class: str = "general", model_id: str = "unknown", context_items: int = 0, latency_ms: int = 0, token_cost: int = 0, human_corrections: int = 0, rework_count: int = 0, verification_failures: int = 0) -> BenchmarkObservation:
    return BenchmarkObservation(task_id, plan.digest(), provenance_head(provenance), release_status, regression_status or "omitted", quality_score, len(plan.waves), len(plan.conflicts), len(plan.blocked), tuple(str(x) for x in specialist_results), execution_mode, task_class, model_id, context_items, latency_ms, token_cost, human_corrections, rework_count, verification_failures)


def _recommend_execution_mode(recent: Sequence[BenchmarkObservation]) -> tuple[str, str]:
    grouped: dict[tuple[str, str], list[BenchmarkObservation]] = {}
    for item in recent:
        grouped.setdefault(item.comparable_key, []).append(item)
    for key in sorted(grouped):
        rows = grouped[key]
        single = [row for row in rows if row.execution_mode == "single-agent"]
        multi = [row for row in rows if row.execution_mode == "multi-agent"]
        single_failures = sum(not row.passed for row in single)
        multi_successes = sum(row.passed for row in multi)
        multi_failures = sum(not row.passed for row in multi)
        if len(single) >= 2 and single_failures >= 2 and len(multi) >= 1 and multi_successes > multi_failures:
            single_quality = sum(row.quality_score for row in single) / len(single)
            multi_quality = sum(row.quality_score for row in multi) / len(multi)
            single_rework = sum(row.rework_count + row.human_corrections for row in single)
            multi_rework = sum(row.rework_count + row.human_corrections for row in multi)
            if multi_quality >= single_quality and multi_rework <= single_rework:
                return "multi-agent", f"comparative evidence for task class {key[0]} supports coordinated execution"
    return "single-agent", "no sufficiently repeated comparative evidence justifies additional agents"


def recommend_plan(history: BenchmarkHistory | Iterable[BenchmarkObservation], *, requested_mutation_mode: str = "bounded", requested_support_limit: int = 2, min_samples: int = 3) -> AdaptiveRecommendation:
    if requested_mutation_mode not in MUTATION_ORDER:
        raise ValueError("unsupported requested mutation mode")
    if requested_support_limit < 0 or min_samples < 1:
        raise ValueError("support limit and min_samples must be valid")
    observations = list(history.observations if isinstance(history, BenchmarkHistory) else history)
    recent = observations[-max(min_samples, 10):]
    if len(recent) < min_samples:
        return AdaptiveRecommendation(requested_mutation_mode, 0, ("insufficient benchmark history; single-agent is the default",), "none", "single-agent", len(recent), 0)

    failures = sum(not item.passed for item in recent)
    regression_failures = sum(item.regression_status == "failed" for item in recent)
    conflict_runs = sum(item.conflict_count > 0 for item in recent)
    conflict_rate = conflict_runs / len(recent)
    blocked_runs = sum(item.blocked_count > 0 for item in recent)
    verification_failures = sum(item.verification_failures > 0 for item in recent)
    correction_or_rework = sum(item.human_corrections + item.rework_count for item in recent)
    average_score = sum(item.quality_score for item in recent) / len(recent)
    execution_mode, execution_reason = _recommend_execution_mode(recent)
    groups = {item.comparable_key for item in recent}
    comparable_pairs = sum(1 for group in groups if sum(1 for row in recent if row.comparable_key == group) >= 2)

    mode = requested_mutation_mode
    support = requested_support_limit
    reasons = [execution_reason]
    if failures or regression_failures or verification_failures:
        mode = MUTATION_ORDER[max(0, MUTATION_ORDER.index(mode) - 1)]
        reasons.append("failed releases, regressions, or verification tighten mutation posture")
    if conflict_rate >= 0.5 or blocked_runs or correction_or_rework > len(recent):
        support = min(support, 1)
        reasons.append("recent conflicts, coordination friction, blocked work, correction, or rework caps specialist support")
    elif average_score >= 95 and conflict_rate <= 0.2 and not failures and not correction_or_rework:
        support = min(requested_support_limit + 1, 3)
        reasons.append("repeated clean outcomes permit one extra support specialist")
    if execution_mode == "single-agent":
        support = 0

    if failures == 0 and regression_failures == 0 and verification_failures == 0 and average_score >= 95 and len(recent) >= 3:
        confidence = "high"
    elif len(recent) >= 5 or comparable_pairs >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    return AdaptiveRecommendation(mode, support, tuple(reasons), confidence, execution_mode, len(recent), comparable_pairs)


def apply_recommendation(requested_mutation_mode: str, requested_support_limit: int, recommendation: AdaptiveRecommendation, *, allowed_mutation_modes: Iterable[str] = MUTATION_ORDER) -> tuple[str, int]:
    allowed = set(allowed_mutation_modes)
    mode = recommendation.mutation_mode if recommendation.mutation_mode in allowed else requested_mutation_mode
    return mode, min(requested_support_limit, recommendation.support_limit if recommendation.support_limit >= 0 else requested_support_limit)
