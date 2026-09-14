#!/usr/bin/env python3
"""Executable context acquisition pipeline with one immutable evidence envelope."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from .context_broker import ContextBroker, ContextCandidate
    from .context_planner import EvidenceCandidate, plan_context, select_evidence
    from portable.repository_intelligence import RepositoryIntelligence
    from portable.semantic_addressing import SymbolLocator
except ImportError:
    from context_broker import ContextBroker, ContextCandidate
    from context_planner import EvidenceCandidate, plan_context, select_evidence
    from repository_intelligence import RepositoryIntelligence
    from semantic_addressing import SymbolLocator


@dataclass(frozen=True, slots=True)
class ContextEvidenceItem:
    evidence_id: str
    kind: str
    source: str
    text: str
    relevance: float
    confidence: float
    freshness: float
    digest: str


@dataclass(frozen=True, slots=True)
class ContextEvidence:
    """Immutable context/evidence envelope carried across execution and rollout."""

    task_id: str
    query: str
    phase: str
    risk: str
    intent_digest: str
    context_plan_digest: str
    repository_snapshot_digest: str
    selected_paths: tuple[str, ...]
    symbol_refs: tuple[str, ...]
    graph_paths: tuple[str, ...]
    items: tuple[ContextEvidenceItem, ...]
    evidence_digest: str
    token_estimate: int
    unknowns: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def deployment_binding(self) -> dict[str, str]:
        return {
            "intent_digest": self.intent_digest,
            "repository_snapshot_digest": self.repository_snapshot_digest,
            "context_plan_digest": self.context_plan_digest,
            "evidence_digest": self.evidence_digest,
        }


class ContextAcquisitionPipeline:
    """DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE.

    One immutable ContextEvidence object is returned. Downstream stages carry its
    digest rather than rebuilding context, so verification and rollout decisions
    can be tied to exactly the evidence used during execution.
    """

    def __init__(self, root: str | Path, *, budget_chars: int | None = None, max_items: int | None = None) -> None:
        self.root = Path(root).resolve()
        self.repository = RepositoryIntelligence(self.root)
        self._broker = ContextBroker(
            budget_chars=budget_chars if budget_chars is not None else 14000,
            max_items=max_items if max_items is not None else 18,
        )

    def acquire(
        self,
        *,
        task_id: str,
        query: str,
        phase: str,
        intent_digest: str,
        risk: str = "medium",
        uncertainty: str = "medium",
        policy_strategy: str | None = None,
        extra_evidence: Iterable[EvidenceCandidate] = (),
        pack: bool = False,
    ) -> ContextEvidence:
        plan = plan_context(phase=phase, risk=risk, uncertainty=uncertainty, policy_strategy=policy_strategy)
        semantic = self.repository.retrieve(
            query,
            token_budget=max(1, min(plan.budget, 8000)),
            max_files=min(plan.max_items, 12),
            context_lines=20,
            graph_hops=2,
        )
        locator = SymbolLocator(self.repository.index)
        symbol_refs = self._resolve_symbols(locator, query)

        candidates: list[EvidenceCandidate] = list(extra_evidence)
        for chunk in semantic.chunks:
            candidates.append(EvidenceCandidate(
                evidence_id=f"code:{chunk.path}:{chunk.start_line}:{chunk.end_line}",
                kind="semantic",
                text=chunk.text,
                relevance=max(0.0, min(1.0, chunk.score / 10.0)),
                confidence=0.9,
                freshness=1.0,
                cost=max(1, chunk.tokens),
                source=chunk.path,
            ))
        candidates.append(EvidenceCandidate(
            evidence_id="graph:" + semantic.snapshot_digest[:16],
            kind="graph",
            text=json.dumps(semantic.graph_trace.as_dict(), sort_keys=True),
            relevance=0.8 if semantic.graph_trace.expanded_paths else 0.3,
            confidence=0.9,
            freshness=1.0,
            cost=max(1, len(semantic.graph_trace.expanded_paths) * 8),
            source="CodebaseIndex.graph",
        ))
        if pack:
            broad = self.repository.pack(token_budget=max(1, min(plan.budget // 2, 6000)), compress=True)
            candidates.append(EvidenceCandidate(
                evidence_id="pack:" + broad.snapshot_digest[:16],
                kind="repository-pack",
                text=broad.as_text(),
                relevance=0.5,
                confidence=0.95,
                freshness=1.0,
                cost=max(1, broad.token_estimate),
                source="RepositoryIntelligence.pack",
            ))

        selected = select_evidence(candidates, budget=plan.budget, max_items=plan.max_items)
        self._broker.register_many(
            ContextCandidate(
                item.evidence_id,
                item.kind,
                f"selected:{item.source}",
                lambda text=item.text: text,
                relevance=item.relevance,
                confidence=item.confidence,
                freshness=item.freshness,
                cost=item.cost,
                phase=phase,
            )
            for item in selected
        )
        leases = self._broker.discover(query, phase=phase, budget_chars=plan.budget, max_items=plan.max_items)
        by_id = {item.evidence_id: item for item in selected}
        items = tuple(
            ContextEvidenceItem(
                lease.context_id,
                lease.kind,
                by_id[lease.context_id].source,
                lease.text,
                round(lease.score, 6),
                by_id[lease.context_id].confidence,
                by_id[lease.context_id].freshness,
                lease.digest,
            )
            for lease in leases
            if lease.context_id in by_id
        )
        plan_digest = _digest({
            "phase": plan.phase, "modes": plan.retrieval_modes, "budget": plan.budget,
            "max_items": plan.max_items, "fresh": plan.require_fresh_verification,
            "strategy": plan.policy_strategy,
        })
        evidence_digest = _digest({
            "task_id": task_id, "query": query, "intent_digest": intent_digest,
            "context_plan_digest": plan_digest, "repository_snapshot_digest": semantic.snapshot_digest,
            "items": [asdict(item) for item in items],
        })
        return ContextEvidence(
            task_id=str(task_id), query=str(query), phase=plan.phase, risk=str(risk).lower(),
            intent_digest=str(intent_digest), context_plan_digest=plan_digest,
            repository_snapshot_digest=semantic.snapshot_digest, selected_paths=semantic.relevant_paths,
            symbol_refs=tuple(symbol_refs), graph_paths=semantic.graph_trace.expanded_paths,
            items=items, evidence_digest=evidence_digest,
            token_estimate=sum(max(1, len(item.text.split())) for item in items),
            unknowns=semantic.unknowns,
        )

    def release(self, evidence: ContextEvidence) -> None:
        self._broker.release(item.evidence_id for item in evidence.items)

    def refresh(self) -> None:
        self.repository.refresh()

    @staticmethod
    def _resolve_symbols(locator: SymbolLocator, query: str) -> list[str]:
        refs: list[str] = []
        for token in (x.strip(".,:()[]{}") for x in query.split()):
            if len(token) < 3 or not token[:1].isalpha():
                continue
            refs.extend(address.ref for address in locator.find(token))
        return sorted(set(refs))[:16]


def _digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


__all__ = ["ContextEvidence", "ContextEvidenceItem", "ContextAcquisitionPipeline"]
