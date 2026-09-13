"""Provider-native capability discovery and deterministic routing for AER.

Provider support is evidence-driven. AER chooses a native provider when its
capability is available, otherwise uses a governed fallback. Model/provider
fallback chains are explicit and deterministic so a transient provider failure
does not silently change the engineering contract.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


CAPABILITIES = (
    "agent",
    "subagent",
    "hooks",
    "session_resume",
    "structured_output",
    "tool_interception",
    "mcp",
    "background_execution",
)


@dataclass(frozen=True)
class ProviderCapability:
    provider: str
    command: str | None
    version: str | None
    capabilities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    priority: int = 100

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class CapabilityRequest:
    capability: str
    preferred_providers: tuple[str, ...] = ()
    allow_fallback: bool = True
    required_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutingDecision:
    provider: str
    capability: str
    native: bool
    reason: str
    command: str | None = None
    fallback_chain: tuple[str, ...] = ()


@dataclass(frozen=True)
class FallbackPolicy:
    providers: tuple[str, ...]
    max_attempts: int = 3
    fail_closed: bool = True


DEFAULT_PROVIDERS: dict[str, tuple[str, ...]] = {
    "claude": ("agent", "subagent", "hooks", "session_resume", "structured_output", "tool_interception", "mcp", "background_execution"),
    "codex": ("agent", "subagent", "session_resume", "structured_output", "mcp"),
    "gemini": ("agent", "subagent", "hooks", "session_resume", "structured_output", "mcp"),
    "copilot": ("agent", "subagent", "hooks", "structured_output", "mcp"),
}


class ProviderFabric:
    """Discover providers and produce stable native/fallback routing decisions."""

    def __init__(self, manifest_dir: Path | str | None = None) -> None:
        self.manifest_dir = Path(manifest_dir or (Path.home() / ".aer" / "providers")).expanduser()

    def discover(self, *, refresh: bool = False) -> dict[str, ProviderCapability]:
        discovered: dict[str, ProviderCapability] = {}
        for provider, capabilities in DEFAULT_PROVIDERS.items():
            command = shutil.which(provider)
            version = self._version(command) if command else None
            evidence: list[str] = []
            priority = 100
            models: tuple[str, ...] = ()
            if command:
                evidence.extend((f"command:{command}", f"version:{version or 'unknown'}"))
            manifest = self._manifest(provider)
            if manifest:
                capabilities = tuple(sorted(set(capabilities) | set(manifest.get("capabilities", []))))
                models = tuple(str(v) for v in manifest.get("models", []) if isinstance(v, str))
                priority = int(manifest.get("priority", 100))
                evidence.append("manifest")
            if command or manifest:
                discovered[provider] = ProviderCapability(provider, command, version, tuple(sorted(capabilities)), tuple(evidence), models, priority)
        if refresh:
            self.persist(discovered)
        return discovered

    def route(self, request: CapabilityRequest, providers: Mapping[str, ProviderCapability] | None = None) -> RoutingDecision:
        if request.capability not in CAPABILITIES:
            raise ValueError(f"unsupported capability: {request.capability}")
        available = providers or self.discover()
        candidates = self._candidate_order(request.preferred_providers, available)
        for name in candidates:
            capability = available.get(name)
            if capability and capability.supports(request.capability) and all(capability.supports(item) for item in request.required_capabilities):
                return RoutingDecision(name, request.capability, True, "native provider capability discovered", capability.command, tuple(candidates))
        if request.allow_fallback:
            return RoutingDecision("aer", request.capability, False, "no native capability discovered; use AER fallback", None, tuple(candidates))
        raise RuntimeError(f"no provider supports capability: {request.capability}")

    def fallback_policy(self, preferred: Sequence[str] = ()) -> FallbackPolicy:
        available = self.discover()
        ordered = self._candidate_order(tuple(preferred), available)
        return FallbackPolicy(tuple(ordered), max_attempts=max(1, min(5, len(ordered))), fail_closed=True)

    def route_model(self, model: str | None = None, *, preferred_providers: Sequence[str] = (), required_capabilities: Sequence[str] = ()) -> RoutingDecision:
        available = self.discover()
        ordered = self._candidate_order(tuple(preferred_providers), available)
        needle = (model or "").lower().strip()
        for name in ordered:
            capability = available[name]
            if required_capabilities and not all(capability.supports(item) for item in required_capabilities):
                continue
            if not needle or not capability.models or any(needle in candidate.lower() for candidate in capability.models):
                return RoutingDecision(name, "agent", True, "model/provider selected from discovered routing matrix", capability.command, tuple(ordered))
        return RoutingDecision("aer", "agent", False, "no matching provider/model evidence; use AER fallback", None, tuple(ordered))

    def persist(self, providers: Mapping[str, ProviderCapability]) -> Path:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        target = self.manifest_dir / "capabilities.json"
        temp = target.with_suffix(".tmp")
        payload = {name: asdict(value) for name, value in sorted(providers.items())}
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return target

    def _candidate_order(self, preferred: tuple[str, ...], available: Mapping[str, ProviderCapability]) -> list[str]:
        ordered: list[str] = []
        for name in preferred:
            if name in available and name not in ordered:
                ordered.append(name)
        for name, spec in sorted(available.items(), key=lambda item: (item[1].priority, item[0])):
            if name not in ordered:
                ordered.append(name)
        return ordered

    def _manifest(self, provider: str) -> dict[str, Any] | None:
        path = self.manifest_dir / f"{provider}.json"
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _version(command: str | None) -> str | None:
        if not command:
            return None
        try:
            result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.SubprocessError):
            return None
        text = (result.stdout or result.stderr).strip().splitlines()
        return text[0][:200] if text else None


__all__ = ["CAPABILITIES", "CapabilityRequest", "ProviderCapability", "ProviderFabric", "RoutingDecision", "FallbackPolicy"]
