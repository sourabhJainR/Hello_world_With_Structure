"""Evidence-driven adaptive planning with a single-agent-first execution posture.

The planner is intentionally small: it observes outcomes and recommends the
least complicated execution shape that has evidence of working. It does not
execute tools, grant permissions, or require a particular model/provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

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
        for value in (self.wave_count, self.conflict_count, self.blocked_count):
            if value < 0:
                raise ValueError("benchmark counts cannot be negative")

    @property
    def passed(self) -> bool:
        return self.release_status == "passed" and self.regression_status != "failed"

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
            history.add(
                BenchmarkObservation(
                    str(data["task_id"]),
                    str(data["plan_digest"]),
                    str(data.get("provenance_head", "")),
                    str(data["release_status"]),
                    str(data["regression_status"]),
                    int(data["quality_score"]),
                    int(data["wave_count"]),
                    int(data["conflict_count"]),
                    int(data["blocked_count"]),
                    tuple(str(x) for x in data.get("specialist_results", ())),
                    str(data.get("execution_mode", "single-agent")),
                )
            )
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

    def __post_init__(self) -> None:
        if self.mutation_mode not in MUTATION_ORDER:
            raise ValueError("unsupported mutation mode")
        if self.support_limit < 0:
            raise ValueError("support_limit cannot be negative")
        if self.confidence not in {"none", "low", "medium", "high"}:
            raise ValueError("unsupported confidence")
        if self.execution_mode not in EXECUTION_ORDER:
            raise ValueError("unsupported execution mode")

    def as_dict(self) -> dict[str, object]:
        return {
            "mutation_mode": self.mutation_mode,
            "support_limit": self.support_limit,
            "reasons": list(self.reasons),
            "confidence": self.confidence,
            "execution_mode": self.execution_mode,
        }


def provenance_head(ledger: ProvenanceLedger) -> str:
    ledger.verify()
    return ledger.records[-1].record_hash if ledger.records else ""


def observe_run(
    *,
    task_id: str,
    plan: ExecutionPlan,
    provenance: ProvenanceLedger,
    release_status: str,
    regression_status: str | None,
    quality_score: int,
    specialist_results: Sequence[str] = (),
    execution_mode: str = "single-agent",
) -> BenchmarkObservation:
    return BenchmarkObservation(
        task_id=task_id,
        plan_digest=plan.digest(),
        provenance_head=provenance_head(provenance),
        release_status=release_status,
        regression_status=regression_status or "omitted",
        quality_score=quality_score,
        wave_count=len(plan.waves),
        conflict_count=len(plan.conflicts),
        blocked_count=len(plan.blocked),
        specialist_results=tuple(str(x) for x in specialist_results),
        execution_mode=execution_mode,
    )


def _recommend_execution_mode(recent: Sequence[BenchmarkObservation]) -> tuple[str, str]:
    """Choose the least complicated mode supported by observed evidence.

    A single agent is the default because every additional agent adds context
    transfer, coordination, and merge cost. Multi-agent execution is promoted
    only when the history contains evidence that it improved outcomes: recent
    single-agent attempts failed while multi-agent attempts passed.
    """
    if not recent:
        return "single-agent", "no execution history: prefer the simplest path"

    single = [item for item in recent if item.execution_mode == "single-agent"]
    multi = [item for item in recent if item.execution_mode == "multi-agent"]
    single_failures = sum(not item.passed for item in single)
    multi_successes = sum(item.passed for item in multi)
    multi_failures = sum(not item.passed for item in multi)

    if single_failures and multi_successes > 0 and multi_successes >= multi_failures:
        return "multi-agent", "multi-agent execution has evidence of recovering work that single-agent execution could not complete"
    if single and all(item.passed for item in single):
        return "single-agent", "recent single-agent work passed; avoid coordination cost until evidence says otherwise"
    return "single-agent", "insufficient comparative evidence to justify additional agents"


def recommend_plan(
    history: BenchmarkHistory | Iterable[BenchmarkObservation],
    *,
    requested_mutation_mode: str = "bounded",
    requested_support_limit: int = 2,
    min_samples: int = 3,
) -> AdaptiveRecommendation:
    """Recommend a bounded next-run posture from historical execution outcomes.

    The execution shape is adaptive but single-agent-first. History can promote
    multi-agent execution only when comparative evidence shows that it helps.
    No recommendation can expand host permissions or bypass policy bounds.
    """
    if requested_mutation_mode not in MUTATION_ORDER:
        raise ValueError("unsupported requested mutation mode")
    if requested_support_limit < 0 or min_samples < 1:
        raise ValueError("support limit and min_samples must be valid")
    observations = list(history.observations if isinstance(history, BenchmarkHistory) else history)
    recent = observations[-max(min_samples, 10) :]
    if len(recent) < min_samples:
        return AdaptiveRecommendation(
            requested_mutation_mode,
            0,
            ("insufficient benchmark history; single-agent is the default",),
            "none",
            "single-agent",
        )

    failures = sum(not item.passed for item in recent)
    regression_failures = sum(item.regression_status == "failed" for item in recent)
    conflict_runs = sum(item.conflict_count > 0 for item in recent)
    blocked_runs = sum(item.blocked_count > 0 for item in recent)
    average_score = sum(item.quality_score for item in recent) / len(recent)
    conflict_rate = conflict_runs / len(recent)
    execution_mode, execution_reason = _recommend_execution_mode(recent)

    mode = requested_mutation_mode
    support = requested_support_limit
    reasons: list[str] = [execution_reason]

    if failures or regression_failures:
        target_index = max(0, MUTATION_ORDER.index(mode) - 1)
        if regression_failures:
            reasons.append("recent artifact regressions tighten mutation posture")
        if failures:
            reasons.append("recent release failures tighten execution posture")
        mode = MUTATION_ORDER[target_index]

    if conflict_rate >= 0.5 or blocked_runs:
        support = min(support, 1)
        reasons.append("frequent conflicts or blocked work caps support specialists")
    elif average_score >= 95 and conflict_rate <= 0.2 and not failures:
        support = min(requested_support_limit + 1, 3)
        reasons.append("strong recent quality with low conflict permits one extra support specialist")

    # Single-agent means no support agents. This is the key simplification: the
    # support budget is available only when evidence promotes a team execution.
    if execution_mode == "single-agent":
        support = 0

    if average_score >= 95 and failures == 0 and regression_failures == 0:
        confidence = "high"
    elif len(recent) >= 5:
        confidence = "medium"
    else:
        confidence = "low"
    return AdaptiveRecommendation(mode, support, tuple(reasons), confidence, execution_mode)


def apply_recommendation(
    requested_mutation_mode: str,
    requested_support_limit: int,
    recommendation: AdaptiveRecommendation,
    *,
    allowed_mutation_modes: Iterable[str] = MUTATION_ORDER,
) -> tuple[str, int]:
    """Apply an adaptive recommendation without escaping host policy bounds."""
    allowed = set(allowed_mutation_modes)
    mode = recommendation.mutation_mode if recommendation.mutation_mode in allowed else requested_mutation_mode
    return mode, min(requested_support_limit, recommendation.support_limit if recommendation.support_limit >= 0 else requested_support_limit)
