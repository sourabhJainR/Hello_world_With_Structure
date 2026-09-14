"""Provider-neutral agent patterns adapted from proven open-source LLM apps.

The module intentionally contains only deterministic orchestration contracts. It
borrows five useful patterns without importing a second agent framework:

* least-privilege specialist routing (specialist -> bounded tool set)
* research fan-out followed by evidence-aware synthesis
* mixture-of-agents consensus with an explicit judge
* self-improvement through one-change-at-a-time evaluation
* diff scope checking to catch work that drifted from intent

LLMs, tools and external services stay behind callbacks supplied by the host.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence


_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")


def _tokens(value: str) -> set[str]:
    return {part.lower() for part in _TOKEN_RE.findall(value) if len(part) > 1}


@dataclass(frozen=True)
class Specialist:
    """A specialist with an explicit capability and tool boundary."""

    name: str
    capabilities: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    risk: str = "medium"
    priority: int = 0

    def covers(self, required: Iterable[str]) -> int:
        wanted = set(required)
        return len(wanted.intersection(self.capabilities))


@dataclass(frozen=True)
class RouteRequest:
    task: str
    required_capabilities: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    max_risk: str = "high"


@dataclass(frozen=True)
class RouteDecision:
    specialist: str
    tools: tuple[str, ...]
    coverage: float
    reason: str


_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class SpecialistRouter:
    """Route work to the smallest suitable specialist/tool boundary."""

    def __init__(self, specialists: Sequence[Specialist]) -> None:
        if not specialists:
            raise ValueError("at least one specialist is required")
        names = [item.name for item in specialists]
        if len(set(names)) != len(names):
            raise ValueError("specialist names must be unique")
        self._specialists = tuple(specialists)

    def route(self, request: RouteRequest) -> RouteDecision:
        if request.max_risk not in _RISK_RANK:
            raise ValueError(f"invalid max risk: {request.max_risk}")
        wanted = set(request.required_capabilities)
        allowed = set(request.allowed_tools)
        ranked: list[tuple[tuple[int, int, int, int], Specialist, set[str]]] = []
        for specialist in self._specialists:
            if _RISK_RANK[specialist.risk] > _RISK_RANK[request.max_risk]:
                continue
            coverage_count = specialist.covers(wanted)
            if wanted and coverage_count == 0:
                continue
            bounded_tools = set(specialist.tools)
            if allowed:
                bounded_tools &= allowed
            ranked.append(
                (
                    (coverage_count, specialist.priority, -len(bounded_tools), -_RISK_RANK[specialist.risk]),
                    specialist,
                    bounded_tools,
                )
            )
        if not ranked:
            raise RuntimeError("no specialist satisfies the capability and risk constraints")
        _, selected, tools = max(ranked, key=lambda item: item[0])
        coverage = 1.0 if not wanted else selected.covers(wanted) / len(wanted)
        return RouteDecision(
            selected.name,
            tuple(sorted(tools)),
            coverage,
            "specialist selected by capability coverage, priority, risk and least-privilege tool access",
        )


@dataclass(frozen=True)
class ResearchTask:
    id: str
    question: str
    capabilities: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchPlan:
    tasks: tuple[ResearchTask, ...]
    waves: tuple[tuple[str, ...], ...]
    digest: str


class ResearchPlanner:
    """Create bounded parallel research waves from independent questions."""

    def build(self, questions: Sequence[str], capabilities: Mapping[str, tuple[str, ...]] | None = None) -> ResearchPlan:
        if not questions:
            raise ValueError("at least one research question is required")
        capabilities = capabilities or {}
        tasks = tuple(
            ResearchTask(f"research-{index + 1}", question.strip(), capabilities.get(question, ()))
            for index, question in enumerate(questions)
            if question.strip()
        )
        if not tasks:
            raise ValueError("research questions cannot be empty")
        waves = (tuple(task.id for task in tasks),)
        digest = hashlib.sha256(
            "|".join(f"{task.id}:{task.question}:{','.join(task.capabilities)}" for task in tasks).encode()
        ).hexdigest()
        return ResearchPlan(tasks, waves, digest)


@dataclass(frozen=True)
class EvidenceItem:
    source: str
    claim: str
    confidence: float = 0.0


@dataclass(frozen=True)
class ConsensusResult:
    answer: str
    selected: tuple[int, ...]
    agreement: float
    evidence: tuple[EvidenceItem, ...] = ()


class MixtureOfAgents:
    """Collect independent answers and let a supplied judge synthesize them."""

    def run(
        self,
        answers: Sequence[str],
        judge: Callable[[Sequence[str]], tuple[str, Sequence[int], float]],
        evidence: Sequence[EvidenceItem] = (),
    ) -> ConsensusResult:
        if not answers:
            raise ValueError("at least one answer is required")
        answer, selected, agreement = judge(tuple(answers))
        selected_tuple = tuple(sorted({index for index in selected if 0 <= index < len(answers)}))
        if not answer.strip():
            raise ValueError("judge returned an empty answer")
        if not 0.0 <= agreement <= 1.0:
            raise ValueError("agreement must be between 0 and 1")
        return ConsensusResult(answer, selected_tuple, agreement, tuple(evidence))


@dataclass(frozen=True)
class OptimizationRound:
    round_number: int
    score: float
    kept: bool
    diagnosis: str
    change: str


@dataclass(frozen=True)
class OptimizationResult:
    baseline_score: float
    final_score: float
    rounds: tuple[OptimizationRound, ...]
    artifact: str


class OneChangeOptimizer:
    """Improve an artifact only when one targeted change raises its score."""

    def optimize(
        self,
        artifact: str,
        *,
        evaluate: Callable[[str], float],
        diagnose: Callable[[str, float], str],
        mutate: Callable[[str, str], str],
        max_rounds: int = 5,
    ) -> OptimizationResult:
        if max_rounds < 1:
            raise ValueError("max_rounds must be positive")
        current = artifact
        baseline = self._score(evaluate(current))
        score = baseline
        rounds: list[OptimizationRound] = []
        for number in range(1, max_rounds + 1):
            diagnosis = diagnose(current, score).strip()
            if not diagnosis:
                break
            candidate = mutate(current, diagnosis)
            if not isinstance(candidate, str) or not candidate.strip():
                raise ValueError("mutate must return a non-empty artifact")
            candidate_score = self._score(evaluate(candidate))
            kept = candidate_score > score
            before = current
            if kept:
                current, score = candidate, candidate_score
            rounds.append(OptimizationRound(number, candidate_score, kept, diagnosis, self._digest_change(before, candidate)))
        return OptimizationResult(baseline, score, tuple(rounds), current)

    @staticmethod
    def _score(value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("evaluation score must be between 0 and 1")
        return float(value)

    @staticmethod
    def _digest_change(before: str, after: str) -> str:
        return hashlib.sha256(f"{before}\n---\n{after}".encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ScopeFinding:
    path: str
    relatedness: float
    classification: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScopeReport:
    findings: tuple[ScopeFinding, ...]
    likely_creep: int
    digest: str


class ScopeChecker:
    """Detect likely scope drift without judging whether a change is correct."""

    def check(self, intent: str, changed_paths: Sequence[str]) -> ScopeReport:
        intent_tokens = _tokens(intent)
        findings: list[ScopeFinding] = []
        for path in changed_paths:
            path_tokens = _tokens(path)
            shared = len(intent_tokens.intersection(path_tokens))
            relatedness = shared / max(1, len(intent_tokens))
            reasons: list[str] = []
            lower = path.lower()
            if lower.endswith((".lock", "requirements.txt", "pyproject.toml", "package.json", "package-lock.json")):
                reasons.append("dependency manifest changed")
            if "/.github/" in lower or lower.startswith(".github/") or "/ci/" in lower:
                reasons.append("CI/configuration surface changed")
            if not path_tokens.intersection(intent_tokens):
                reasons.append("no shared intent/path tokens")
            classification = "in_scope" if relatedness > 0 or not reasons else "likely_creep"
            if reasons and "no shared intent/path tokens" in reasons:
                classification = "likely_creep"
            findings.append(ScopeFinding(path, round(relatedness, 4), classification, tuple(reasons)))
        findings.sort(key=lambda item: (item.classification != "likely_creep", item.path))
        digest = hashlib.sha256("|".join(f"{x.path}:{x.classification}" for x in findings).encode()).hexdigest()
        return ScopeReport(tuple(findings), sum(x.classification == "likely_creep" for x in findings), digest)


__all__ = [
    "ConsensusResult",
    "EvidenceItem",
    "MixtureOfAgents",
    "OneChangeOptimizer",
    "OptimizationResult",
    "OptimizationRound",
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchTask",
    "RouteDecision",
    "RouteRequest",
    "ScopeChecker",
    "ScopeFinding",
    "ScopeReport",
    "Specialist",
    "SpecialistRouter",
]
