"""Bind one context/evidence envelope to executable artifact rollout transitions."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from .agency_release_lifecycle import ArtifactRef, ArtifactStore, ReleaseState

@dataclass(frozen=True, slots=True)
class VerificationReceipt:
    artifact_digest: str
    context_evidence_digest: str
    checks: tuple[str, ...]
    verification_digest: str
    def as_dict(self) -> dict[str, object]:
        return {"artifact_digest": self.artifact_digest, "context_evidence_digest": self.context_evidence_digest, "checks": list(self.checks), "verification_digest": self.verification_digest}

@dataclass(frozen=True, slots=True)
class ReviewReceipt:
    """Content-addressed review proof bound to the verified artifact and evidence."""
    artifact_digest: str
    context_evidence_digest: str
    verification_digest: str
    findings: tuple[str, ...]
    review_digest: str
    def as_dict(self) -> dict[str, object]:
        return {"artifact_digest": self.artifact_digest, "context_evidence_digest": self.context_evidence_digest, "verification_digest": self.verification_digest, "findings": list(self.findings), "review_digest": self.review_digest}

@dataclass(frozen=True, slots=True)
class ContextBoundRelease:
    store: ArtifactStore
    context_evidence: Any
    @property
    def evidence_digest(self) -> str:
        value = str(getattr(self.context_evidence, "evidence_digest", "") or "")
        if not value: raise ValueError("context evidence must expose a non-empty evidence_digest")
        return value
    def verify(self, artifact: ArtifactRef, checks: Mapping[str, bool] | tuple[str, ...] = ()) -> VerificationReceipt:
        if isinstance(checks, Mapping):
            failed = sorted(str(name) for name, passed in checks.items() if not passed)
            if failed: raise ValueError("verification failed: " + ", ".join(failed))
            names = tuple(sorted(str(name) for name in checks))
        else: names = tuple(sorted(str(name) for name in checks))
        payload = {"artifact_digest": artifact.digest, "context_evidence_digest": self.evidence_digest, "checks": names}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        return VerificationReceipt(artifact.digest, self.evidence_digest, names, digest)
    def review(self, artifact: ArtifactRef, verification: VerificationReceipt, findings: tuple[str, ...] | list[str] = ()) -> ReviewReceipt:
        """Mandatory gate between verification and rollout; unresolved findings fail closed."""
        self._validate_verification(artifact, verification)
        normalized = tuple(sorted(str(f).strip() for f in findings if str(f).strip()))
        if normalized: raise ValueError("review gate failed: " + "; ".join(normalized))
        payload = {"artifact_digest": artifact.digest, "context_evidence_digest": self.evidence_digest, "verification_digest": verification.verification_digest, "findings": normalized}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        return ReviewReceipt(artifact.digest, self.evidence_digest, verification.verification_digest, normalized, digest)
    def shadow(self, artifact: ArtifactRef, *, reason: str = "shadow evaluation") -> ReleaseState:
        return self._transition("shadow", artifact, reason)
    def canary(self, artifact: ArtifactRef, *, reason: str = "canary evaluation") -> ReleaseState:
        return self._transition("canary", artifact, reason)
    def promote(self, artifact: ArtifactRef, *, reason: str = "promotion gate passed", verification: VerificationReceipt | None = None, review: ReviewReceipt | None = None, verification_digest: str | None = None, review_digest: str | None = None) -> ReleaseState:
        if verification is None: raise ValueError("promotion requires a verification receipt")
        self._validate_verification(artifact, verification)
        if review is None: raise ValueError("promotion requires a review receipt")
        self._validate_review(artifact, verification, review)
        return self._transition("promote", artifact, reason, verification_digest=verification.verification_digest, review_digest=review.review_digest)
    def rollback(self, *, reason: str = "rollback gate failed", verification_digest: str | None = None, review_digest: str | None = None) -> ReleaseState:
        return self._transition("rollback", None, reason, verification_digest=verification_digest, review_digest=review_digest)
    def _validate_verification(self, artifact: ArtifactRef, receipt: VerificationReceipt) -> None:
        if receipt.artifact_digest != artifact.digest: raise ValueError("verification receipt belongs to a different artifact")
        if receipt.context_evidence_digest != self.evidence_digest: raise ValueError("verification receipt belongs to different context evidence")
        if not receipt.verification_digest: raise ValueError("verification receipt is missing its digest")
    def _validate_review(self, artifact: ArtifactRef, verification: VerificationReceipt, receipt: ReviewReceipt) -> None:
        if receipt.artifact_digest != artifact.digest: raise ValueError("review receipt belongs to a different artifact")
        if receipt.context_evidence_digest != self.evidence_digest: raise ValueError("review receipt belongs to different context evidence")
        if receipt.verification_digest != verification.verification_digest: raise ValueError("review receipt belongs to a different verification receipt")
        if not receipt.review_digest: raise ValueError("review receipt is missing its digest")
        if receipt.findings: raise ValueError("review receipt contains unresolved findings")
    def _transition(self, action: str, artifact: ArtifactRef | None, reason: str, *, verification_digest: str | None = None, review_digest: str | None = None) -> ReleaseState:
        return self.store.transition(action, artifact, reason, context_evidence_digest=self.evidence_digest, verification_digest=verification_digest, review_digest=review_digest)

def bind_release_context(store_root: str | Path, context_evidence: Any) -> ContextBoundRelease:
    return ContextBoundRelease(ArtifactStore(store_root), context_evidence)

__all__ = ["ContextBoundRelease", "ReviewReceipt", "VerificationReceipt", "bind_release_context"]
