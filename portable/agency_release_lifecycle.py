"""Executable artifact lifecycle for AER release decisions.

The lifecycle turns a PromotionDecision into an observable, reversible state
transition. It is deliberately local and provider-neutral: an artifact is
content-addressed, copied into an immutable store, and referenced by channels.
No deployment platform is required, while platform adapters can mirror the
same transitions later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Mapping


ACTIONS = {"shadow", "canary", "promote", "rollback"}


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    digest: str
    path: str
    size: int

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ReleaseState:
    action: str
    artifact_id: str | None
    digest: str | None
    previous_artifact_id: str | None
    timestamp: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class ArtifactStore:
    """Content-addressed immutable artifact store plus channel pointers."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.artifacts = self.root / "artifacts"
        self.channels = self.root / "channels"
        self.history = self.root / "release-history.jsonl"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.channels.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        if path.is_file():
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.is_dir():
            for item in sorted(p for p in path.rglob("*") if p.is_file()):
                digest.update(item.relative_to(path).as_posix().encode())
                with item.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
        else:
            raise FileNotFoundError(str(path))
        return digest.hexdigest()

    def stage(self, source: str | Path, artifact_id: str) -> ArtifactRef:
        source_path = Path(source).expanduser().resolve()
        if not artifact_id.strip():
            raise ValueError("artifact_id is required")
        digest = self._digest(source_path)
        destination = self.artifacts / digest
        if destination.exists():
            existing = self._digest(destination)
            if existing != digest:
                raise RuntimeError("artifact digest collision detected")
        else:
            temp = self.artifacts / f".{digest}.tmp"
            if temp.exists():
                shutil.rmtree(temp) if temp.is_dir() else temp.unlink()
            if source_path.is_dir():
                shutil.copytree(source_path, temp)
            else:
                temp.mkdir(parents=True)
                shutil.copy2(source_path, temp / source_path.name)
            temp.replace(destination)
        size = sum(p.stat().st_size for p in destination.rglob("*") if p.is_file())
        ref = ArtifactRef(artifact_id, digest, str(destination), size)
        self._write_json(self.artifacts / f"{digest}.json", {"artifact": ref.as_dict()})
        return ref

    def _read_channel(self, channel: str) -> ArtifactRef | None:
        path = self.channels / f"{channel}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        artifact = data.get("artifact")
        return ArtifactRef(**artifact) if isinstance(artifact, dict) else None

    def _set_channel(self, channel: str, ref: ArtifactRef | None) -> None:
        path = self.channels / f"{channel}.json"
        if ref is None:
            path.unlink(missing_ok=True)
            return
        self._write_json(path, {"artifact": ref.as_dict()})

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)

    def state(self) -> Mapping[str, object]:
        shadow = self._read_channel("shadow")
        canary = self._read_channel("canary")
        current = self._read_channel("current")
        return {"shadow": shadow.as_dict() if shadow else None, "canary": canary.as_dict() if canary else None, "current": current.as_dict() if current else None}

    def transition(self, action: str, ref: ArtifactRef | None, reason: str) -> ReleaseState:
        if action not in ACTIONS:
            raise ValueError(f"unsupported release action: {action}")
        if action != "rollback" and ref is None:
            raise ValueError(f"{action} requires an artifact")
        previous = self._read_channel("current")
        if action == "shadow":
            self._set_channel("shadow", ref)
        elif action == "canary":
            self._set_channel("canary", ref)
        elif action == "promote":
            self._set_channel("current", ref)
            self._set_channel("canary", None)
            self._set_channel("shadow", None)
        else:
            if previous is None:
                state = ReleaseState("rollback", None, None, None, datetime.now(timezone.utc).isoformat(), reason + "; no active artifact to replace")
                self._record(state)
                return state
            candidates = [x for x in self._history() if x.get("action") in {"promote", "rollback"} and x.get("artifact_id") and x.get("artifact_id") != previous.artifact_id]
            if not candidates:
                state = ReleaseState("rollback", previous.artifact_id, previous.digest, previous.artifact_id, datetime.now(timezone.utc).isoformat(), reason + "; no previous promoted artifact available")
                self._record(state)
                return state
            target_ref = self._ref_from_history(candidates[-1])
            self._set_channel("current", target_ref)
            self._set_channel("canary", None)
            self._set_channel("shadow", None)
            ref = target_ref
        state = ReleaseState(action, ref.artifact_id if ref else None, ref.digest if ref else None, previous.artifact_id if previous else None, datetime.now(timezone.utc).isoformat(), reason)
        self._record(state)
        return state

    def apply_decision(self, decision: object, artifact: ArtifactRef | None = None) -> ReleaseState:
        action = str(getattr(decision, "action", ""))
        reason = str(getattr(decision, "reason", "release decision"))
        return self.transition(action, None if action == "rollback" else artifact, reason)

    def _record(self, state: ReleaseState) -> None:
        with self.history.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(state.as_dict(), sort_keys=True) + "\n")

    def _history(self) -> list[dict]:
        if not self.history.is_file():
            return []
        values = []
        for line in self.history.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                values.append(value)
        return values

    @staticmethod
    def _ref_from_history(value: Mapping[str, object]) -> ArtifactRef:
        return ArtifactRef(str(value["artifact_id"]), str(value["digest"]), str(value.get("path", "")), int(value.get("size", 0)))


def apply_promotion_decision(store: ArtifactStore, decision: object, artifact: ArtifactRef | None = None) -> ReleaseState:
    """Public integration point used by runtimes and deployment adapters."""
    return store.apply_decision(decision, artifact)
