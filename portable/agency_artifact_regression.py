"""Deterministic artifact fingerprints and regression decisions."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ArtifactSnapshot:
    path: str
    digest: str
    size: int


def snapshot_artifact(path: str | Path) -> ArtifactSnapshot:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    data = p.read_bytes()
    return ArtifactSnapshot(str(p), sha256(data).hexdigest(), len(data))


def fingerprint_paths(paths: Iterable[str | Path]) -> tuple[ArtifactSnapshot, ...]:
    snapshots = [snapshot_artifact(path) for path in paths]
    return tuple(sorted(snapshots, key=lambda x: x.path))


def manifest(snapshots: Iterable[ArtifactSnapshot]) -> str:
    payload = [{"path": s.path, "digest": s.digest, "size": s.size} for s in sorted(snapshots, key=lambda x: x.path)]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RegressionFinding:
    kind: str
    path: str
    detail: str


@dataclass(frozen=True)
class RegressionDecision:
    status: str
    findings: tuple[RegressionFinding, ...]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "passed": self.passed, "findings": [f.__dict__ for f in self.findings]}


def compare_artifacts(
    baseline: Mapping[str, ArtifactSnapshot],
    current: Mapping[str, ArtifactSnapshot],
    allowed_changes: Iterable[str] = (),
) -> RegressionDecision:
    allowed = {str(x) for x in allowed_changes}
    findings: list[RegressionFinding] = []
    for path in sorted(set(baseline) | set(current)):
        if path in allowed:
            continue
        before, after = baseline.get(path), current.get(path)
        if before is None:
            findings.append(RegressionFinding("added", path, "artifact was not present in baseline"))
        elif after is None:
            findings.append(RegressionFinding("removed", path, "artifact is missing from current run"))
        elif before.digest != after.digest or before.size != after.size:
            findings.append(RegressionFinding("changed", path, "artifact digest or size changed"))
    return RegressionDecision("passed" if not findings else "failed", tuple(findings))
