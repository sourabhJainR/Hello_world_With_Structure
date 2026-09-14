"""Bind one context/evidence envelope to executable artifact rollout transitions."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .agency_release_lifecycle import ArtifactRef, ArtifactStore, ReleaseState


@dataclass(frozen=True, slots=True)
class VerificationReceipt:
    """Content-addressed proof that an artifact was verified against the same evidence."""

    artifact_digest: str
    context_evidence_digest: str
    checks: tuple[str, ...]
    verification_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_digest": self.artifact_digest,
            "context_evidence_digest": self.context_evidence_digest,
            "checks": list(self.checks),
            "verification_digest": self.verification_digest,
        }


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

    def verify(self, artifact: ArtifactRef, checks: Mapping[str, bool] | tuple[str, ...] = ()) -> VerificationReceipt:
        """Create a reusable verification receipt before promotion.

        Mapping values are explicit pass/fail checks. A tuple is treated as a
        caller-supplied list of checks that have already passed.
        """
        if isinstance(checks, Mapping):
            failed = sorted(str(name) for name, passed in checks.items() if not passed)
            if failed:
                raise ValueError("verification failed: " + ", ".join(failed))
            names = tuple(sorted(str(name) for name in checks))
        else:
            names = tuple(sorted(str(name) for name in checks))
        payload = {
            "artifact_digest": artifact.digest,
            "context_evidence_digest": self.evidence_digest,
            "checks": names,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
        return VerificationReceipt(artifact.digest, self.evidence_digest, names, digest)

    def shadow(self, artifact: ArtifactRef, *, reason: str = "shadow evaluation") -> ReleaseState:
        return self._transition("shadow", artifact, reason)

    def canary(self, artifact: ArtifactRef, *, reason: str = "canary evaluation") -> ReleaseState:
        return self._transition("canary", artifact, reason)

    def promote(
        self,
        artifact: ArtifactRef,
        *,
        reason: str = "promotion gate passed",
        verification: VerificationReceipt | None = None,
        verification_digest: str | None = None,
    ) -> ReleaseState:
        if verification is not None:
            self._validate_verification(artifact, verification)
            verification_digest = verification.verification_digest
        return self._transition("promote", artifact, reason, verification_digest=verification_digest)

    def rollback(
        self,
        *,
        reason: str = "rollback gate failed",
        verification_digest: str | None = None,
    ) -> ReleaseState:
        return self._transition("rollback", None, reason, verification_digest=verification_digest)

    def _validate_verification(self, artifact: ArtifactRef, receipt: VerificationReceipt) -> None:
        if receipt.artifact_digest != artifact.digest:
            raise ValueError("verification receipt belongs to a different artifact")
        if receipt.context_evidence_digest != self.evidence_digest:
            raise ValueError("verification receipt belongs to different context evidence")
        if not receipt.verification_digest:
            raise ValueError("verification receipt is missing its digest")

    def _transition(
        self,
        action: str,
        artifact: ArtifactRef | None,
        reason: str,
        *,
        verification_digest: str | None = None,
    ) -> ReleaseState:
        return self.store.transition(
            action,
            artifact,
            reason,
            context_evidence_digest=self.evidence_digest,
            verification_digest=verification_digest,
        )


def bind_release_context(store_root: str | Path, context_evidence: Any) -> ContextBoundRelease:
    return ContextBoundRelease(ArtifactStore(store_root), context_evidence)


__all__ = ["ContextBoundRelease", "VerificationReceipt", "bind_release_context"]
