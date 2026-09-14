"""Ragas-inspired evaluation primitives for the coding agency.

These metrics borrow the useful separation used by Ragas: retrieval quality and
answer quality are measured independently. They are deterministic and do not
require an LLM, which keeps the portable runtime cheap and reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text) if len(t) > 1}


def _overlap(a: str, b: str) -> float:
    left, right = _tokens(a), _tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True)
class RetrievalMetrics:
    context_precision: float
    context_recall: float
    path_hit_rate: float

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AnswerMetrics:
    response_relevancy: float
    faithfulness: float
    answer_correctness: float

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CodebaseEvaluation:
    retrieval: RetrievalMetrics
    answer: AnswerMetrics
    unknown_count: int
    score: float
    findings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.score >= 0.80 and self.unknown_count == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "retrieval": self.retrieval.as_dict(),
            "answer": self.answer.as_dict(),
            "unknown_count": self.unknown_count,
            "score": self.score,
            "passed": self.passed,
            "findings": list(self.findings),
        }


def retrieval_metrics(
    retrieved_contexts: Sequence[str],
    *,
    relevant_contexts: Sequence[str] = (),
    retrieved_paths: Sequence[str] = (),
    expected_paths: Sequence[str] = (),
) -> RetrievalMetrics:
    """Measure ranking precision, recall and expected-path coverage.

    Context precision rewards relevant evidence appearing early; context recall
    measures how much of the expected evidence was recovered. When references
    are absent, the corresponding score is neutral rather than guessed.
    """
    if not retrieved_contexts:
        return RetrievalMetrics(0.0, 0.0 if relevant_contexts else 1.0, 0.0 if expected_paths else 1.0)
    precision_terms: list[float] = []
    for rank, context in enumerate(retrieved_contexts, 1):
        if relevant_contexts:
            relevance = max((_overlap(context, ref) for ref in relevant_contexts), default=0.0)
            hit = 1.0 if relevance >= 0.20 else 0.0
        else:
            hit = 1.0
        precision_terms.append(hit / rank)
    precision = _mean(precision_terms)
    recall = 1.0 if not relevant_contexts else _mean(
        1.0 if max((_overlap(ref, ctx) for ctx in retrieved_contexts), default=0.0) >= 0.20 else 0.0
        for ref in relevant_contexts
    )
    if not expected_paths:
        path_hit = 1.0
    else:
        normalized = {p.replace("\\", "/").lower() for p in retrieved_paths}
        path_hit = sum(p.replace("\\", "/").lower() in normalized for p in expected_paths) / len(expected_paths)
    return RetrievalMetrics(round(precision, 4), round(recall, 4), round(path_hit, 4))


def answer_metrics(
    query: str,
    answer: str,
    evidence: Sequence[str],
    *,
    reference: str | None = None,
) -> AnswerMetrics:
    """Score relevance, evidence support and optional reference correctness."""
    relevance = _overlap(query, answer)
    if not answer.strip():
        faithfulness = 0.0
    elif not evidence:
        faithfulness = 0.0
    else:
        claims = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
        supported = sum(
            1 for claim in claims if max((_overlap(claim, source) for source in evidence), default=0.0) >= 0.20
        )
        faithfulness = supported / len(claims) if claims else 0.0
    correctness = relevance if reference is None else _overlap(answer, reference)
    return AnswerMetrics(round(relevance, 4), round(faithfulness, 4), round(correctness, 4))


def evaluate_codebase_answer(
    query: str,
    answer: str,
    evidence: Sequence[str],
    *,
    retrieved_paths: Sequence[str] = (),
    expected_paths: Sequence[str] = (),
    relevant_contexts: Sequence[str] = (),
    reference: str | None = None,
    unknowns: Sequence[str] = (),
) -> CodebaseEvaluation:
    """Produce an auditable scorecard for a codebase question or coding task."""
    retrieval = retrieval_metrics(
        evidence,
        relevant_contexts=relevant_contexts,
        retrieved_paths=retrieved_paths,
        expected_paths=expected_paths,
    )
    answer_score = answer_metrics(query, answer, evidence, reference=reference)
    unknown_count = len(tuple(unknowns))
    score = (
        retrieval.context_precision * 0.25
        + retrieval.context_recall * 0.25
        + retrieval.path_hit_rate * 0.10
        + answer_score.response_relevancy * 0.15
        + answer_score.faithfulness * 0.15
        + answer_score.answer_correctness * 0.10
    )
    findings: list[str] = []
    if retrieval.context_recall < 0.80:
        findings.append("retrieval recall is below 0.80")
    if retrieval.context_precision < 0.80:
        findings.append("retrieval precision is below 0.80")
    if answer_score.faithfulness < 0.80:
        findings.append("answer contains claims not sufficiently supported by retrieved evidence")
    if unknown_count:
        findings.append(f"{unknown_count} explicit unknown(s) remain")
    if unknown_count:
        score *= max(0.0, 1.0 - min(0.5, unknown_count * 0.05))
    return CodebaseEvaluation(retrieval, answer_score, round(score, 4), tuple(findings))
