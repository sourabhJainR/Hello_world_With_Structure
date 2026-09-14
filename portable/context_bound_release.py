"""Bind one context/evidence envelope to executable artifact rollout transitions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agency_release_lifecycle import ArtifactRef, ArtifactStore, ReleaseState


@dataclass(frozen=True, slots=True)
class ContextBoundRelease:
    """Deployment adapter that refuses to detach rollout decisions from evidence."""

    store: ArtifactStore
    context_evidence: Any

    @property
    def evidence_digest(self) -> str:
        value = str(getattr(self.context_evidence, "evidence_digest", "") or "")
        if not value:
            raise ValueError("context evidence must expose a non-empty evidence_digest")
        return value

    def shadow(self, artifact: ArtifactRef, *, reason: str = "shadow evaluation") -> ReleaseState:
        return self._transition("shadow", artifact, reason)

    def canary(self, artifact: ArtifactRef, *, reason: str = "canary evaluation") -> ReleaseState:
        return self._transition("canary", artifact, reason)

    def promote(self, artifact: ArtifactRef, *, reason: str = "promotion gate passed") -> ReleaseState:
        return self._transition("promote", artifact, reason)

    def rollback(self, *, reason: str = "rollback gate failed") -> ReleaseState:
        return self._transition("rollback", None, reason)

    def _transition(self, action: str, artifact: ArtifactRef | None, reason: str) -> ReleaseState:
        binding = self.evidence_digest
        return self.store.transition(action, artifact, f"{reason}; context_evidence_digest={binding}")


def bind_release_context(store_root: str | Path, context_evidence: Any) -> ContextBoundRelease:
    return ContextBoundRelease(ArtifactStore(store_root), context_evidence)


__all__ = ["ContextBoundRelease", "bind_release_context"]
