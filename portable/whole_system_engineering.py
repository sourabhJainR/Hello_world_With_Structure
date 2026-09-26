"""Open-ended, whole-system engineering evaluation for general intelligence.

The evaluator turns software-engineering intent into bounded, novel probes spanning
frontend, backend, data, architecture, quality, security, operations, UX and
requirements completeness. It measures evidence-backed competence rather than
declaring an AGI score.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Callable, Mapping, Sequence


ENGINEERING_DOMAINS: tuple[str, ...] = (
    "requirements",
    "architecture",
    "frontend",
    "backend",
    "data",
    "api",
    "testing",
    "security",
    "performance",
    "observability",
    "operations",
    "documentation",
)


@dataclass(frozen=True)
class EngineeringTask:
    task_id: str
    intent: str
    domain: str
    condition: str
    novelty: float
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringEvaluation:
    task: EngineeringTask
    score: float
    verified: bool
    evidence_ids: tuple[str, ...]
    defects: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngineeringCoverage:
    covered: tuple[str, ...]
    missing: tuple[str, ...]
    scores: Mapping[str, float]
    verified: bool
    completeness_ratio: float
    overall_score: float


class WholeSystemEngineeringEvaluator:
    """Generate and aggregate bounded full-stack engineering probes.

    This is model/topology neutral. An external executor/evaluator can be a
    frontier model, local model, deterministic checker, human review, or a
    composite. The evaluator never grants execution authority.
    """

    def __init__(self, domains: Sequence[str] = ENGINEERING_DOMAINS) -> None:
        normalized = tuple(dict.fromkeys(str(x).strip().lower() for x in domains if str(x).strip()))
        unknown = set(normalized) - set(ENGINEERING_DOMAINS)
        if unknown:
            raise ValueError(f"unknown engineering domains: {sorted(unknown)}")
        if len(normalized) < 2:
            raise ValueError("at least two engineering domains are required")
        self.domains = normalized

    def generate(
        self,
        intent: str,
        *,
        conditions: Sequence[str] = ("novel-input", "constraint-shift", "failure-repair"),
        budget: int = 12,
        required_domains: Sequence[str] = (),
    ) -> tuple[EngineeringTask, ...]:
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent is required")
        conditions = tuple(dict.fromkeys(str(x).strip() for x in conditions if str(x).strip()))
        if not conditions:
            raise ValueError("at least one condition is required")
        budget = min(max(2, int(budget)), len(self.domains) * len(conditions))
        required = tuple(dict.fromkeys(str(x).strip().lower() for x in required_domains if str(x).strip()))
        unknown = set(required) - set(self.domains)
        if unknown:
            raise ValueError(f"unknown required domains: {sorted(unknown)}")

        candidates: list[EngineeringTask] = []
        for domain in self.domains:
            for condition in conditions:
                digest = hashlib.sha256(f"{intent.strip()}|{domain}|{condition}".encode()).hexdigest()
                novelty = 0.5 + int(digest[:8], 16) / 0xFFFFFFFF * 0.5
                criteria = self._criteria(domain, condition)
                candidates.append(EngineeringTask(
                    task_id=digest[:16],
                    intent=intent.strip(),
                    domain=domain,
                    condition=condition,
                    novelty=novelty,
                    acceptance_criteria=criteria,
                ))

        selected: list[EngineeringTask] = []
        seen_domains: set[str] = set()
        for task in candidates:
            if task.domain in required and task.domain not in seen_domains:
                selected.append(task)
                seen_domains.add(task.domain)
        for task in sorted(candidates, key=lambda x: (-x.novelty, x.domain, x.condition)):
            if len(selected) >= budget:
                break
            if task.task_id not in {x.task_id for x in selected}:
                selected.append(task)
                seen_domains.add(task.domain)
        return tuple(selected[:budget])

    def evaluate(
        self,
        tasks: Sequence[EngineeringTask],
        evaluator: Callable[[EngineeringTask], EngineeringEvaluation],
        *,
        minimum_domain_score: float = 0.70,
        minimum_overall_score: float = 0.75,
    ) -> EngineeringCoverage:
        if len(tasks) < 2:
            raise ValueError("at least two tasks are required")
        results = tuple(evaluator(task) for task in tasks)
        if len(results) != len(tasks):
            raise ValueError("evaluator must return one result per task")
        if {r.task.task_id for r in results} != {t.task_id for t in tasks}:
            raise ValueError("evaluation task IDs do not match")
        for result in results:
            if not 0 <= result.score <= 1:
                raise ValueError("scores must be between 0 and 1")
            if result.verified and not result.evidence_ids:
                raise ValueError("verified results require evidence IDs")

        scores: dict[str, list[float]] = {}
        for result in results:
            scores.setdefault(result.task.domain, []).append(result.score)
        domain_scores = {domain: sum(values) / len(values) for domain, values in scores.items()}
        covered = tuple(sorted(domain for domain, score in domain_scores.items() if score >= minimum_domain_score))
        missing = tuple(sorted(domain for domain in self.domains if domain not in domain_scores or domain_scores[domain] < minimum_domain_score))
        verified = all(r.verified and bool(r.evidence_ids) for r in results)
        completeness = len(covered) / len(self.domains)
        overall = sum(r.score for r in results) / len(results)
        if overall < minimum_overall_score:
            verified = False
        return EngineeringCoverage(covered, missing, domain_scores, verified, completeness, overall)

    @staticmethod
    def _criteria(domain: str, condition: str) -> tuple[str, ...]:
        common = ("preserve the stated requirements", "handle failure and edge cases", "provide verification evidence")
        specific = {
            "requirements": ("identify ambiguities and explicit acceptance criteria",),
            "architecture": ("define boundaries, dependencies and trade-offs",),
            "frontend": ("cover state, accessibility, responsive behavior and error UX",),
            "backend": ("cover validation, concurrency, failure handling and compatibility",),
            "data": ("cover schema, migration, integrity and recovery",),
            "api": ("cover contract, versioning, errors and idempotency",),
            "testing": ("include unit, integration and regression coverage",),
            "security": ("identify trust boundaries, authorization and input threats",),
            "performance": ("identify latency, throughput and resource constraints",),
            "observability": ("define logs, metrics, traces and actionable diagnostics",),
            "operations": ("cover deployment, rollback, configuration and health checks",),
            "documentation": ("document behavior, setup, limits and operational decisions",),
        }
        return tuple(common + specific[domain] + (f"adapt to condition: {condition}",))


__all__ = [
    "ENGINEERING_DOMAINS",
    "EngineeringTask",
    "EngineeringEvaluation",
    "EngineeringCoverage",
    "WholeSystemEngineeringEvaluator",
]
