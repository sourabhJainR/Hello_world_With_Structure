#!/usr/bin/env python3
"""Observable agent-turn state machine, usage accounting and decision telemetry."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

STATES = ("idle", "planning", "acting", "observing", "verifying", "deciding", "completed", "repairing", "stopped", "failed")
OBSERVATION_PREFIX = "HARNESS_TOOL_OBSERVATION:"
USAGE_PREFIX = "HARNESS_USAGE:"
CACHE_PREFIX = "HARNESS_CACHE:"


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def estimate_tokens(text: str) -> int:
    """Conservative fallback when a provider does not report token counts."""
    return max(0, (len(text) + 3) // 4)


def _json_lines(output: str, prefix: str) -> list[dict[str, Any]]:
    rows = []
    for line in output.splitlines():
        if not line.startswith(prefix):
            continue
        try:
            value = json.loads(line[len(prefix):].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False

    def finalize(self) -> "TokenUsage":
        if self.total_tokens <= 0:
            self.total_tokens = self.input_tokens + self.output_tokens + self.reasoning_tokens
        return self


@dataclass
class ToolObservation:
    sequence: int
    tool: str
    status: str = "unknown"
    duration_ms: float = 0.0
    result_digest: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheTelemetry:
    provider_reported: bool = False
    hit: bool | None = None
    read_tokens: int = 0
    write_tokens: int = 0
    cache_key: str | None = None
    source: str = "none"


@dataclass
class AgentTurn:
    turn_id: str
    phase: str
    state: str = "idle"
    started_at: str | None = None
    ended_at: str | None = None
    observations: list[ToolObservation] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    cache: CacheTelemetry = field(default_factory=CacheTelemetry)
    context_pages: list[str] = field(default_factory=list)
    context_digest: str | None = None
    decision: dict[str, Any] = field(default_factory=dict)
    evidence_score: float = 0.0
    verification_score: float = 0.0
    uncertainty: float = 1.0


class AgentTurnStateMachine:
    """A provider-neutral state machine. Providers may enrich it; they do not own its semantics."""

    _allowed = {
        "idle": {"planning", "acting", "failed"},
        "planning": {"acting", "failed"},
        "acting": {"observing", "completed", "failed"},
        "observing": {"acting", "verifying", "failed"},
        "verifying": {"deciding", "failed"},
        "deciding": {"acting", "repairing", "stopped", "completed", "failed"},
        "repairing": {"acting", "verifying", "failed"},
        "completed": set(), "stopped": set(), "failed": set(),
    }

    def __init__(self, phase: str, run_dir: Path, turn_id: str):
        self.run_dir = run_dir
        self.turn = AgentTurn(turn_id=turn_id, phase=phase)
        self.path = run_dir / "agent-turns.jsonl"

    def transition(self, state: str, **metadata: Any) -> None:
        if state not in STATES or state not in self._allowed.get(self.turn.state, set()):
            raise ValueError(f"Invalid agent-turn transition {self.turn.state} -> {state}")
        self.turn.state = state
        self._event("state.transition", {"state": state, **metadata})

    def set_context(self, pages: list[str], context_digest: str | None = None) -> None:
        self.turn.context_pages = list(dict.fromkeys(str(p) for p in pages if p))
        self.turn.context_digest = context_digest or digest(self.turn.context_pages)
        self._event("context.lineage", {"page_ids": self.turn.context_pages, "context_digest": self.turn.context_digest})

    def observe_tools(self, output: str) -> None:
        for index, row in enumerate(_json_lines(output, OBSERVATION_PREFIX), start=1):
            observation = ToolObservation(
                sequence=int(row.get("sequence", index)),
                tool=str(row.get("tool", "unknown")),
                status=str(row.get("status", "unknown")),
                duration_ms=float(row.get("duration_ms", 0) or 0),
                result_digest=str(row.get("result_digest") or digest(row.get("result", ""))),
                error=str(row["error"]) if row.get("error") else None,
                metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            )
            self.turn.observations.append(observation)
            self._event("tool.observation", asdict(observation))

    def observe_usage(self, prompt: str, output: str) -> None:
        rows = _json_lines(output, USAGE_PREFIX)
        if rows:
            row = rows[-1]
            usage = TokenUsage(
                input_tokens=int(row.get("input_tokens", 0) or 0),
                output_tokens=int(row.get("output_tokens", 0) or 0),
                cached_input_tokens=int(row.get("cached_input_tokens", 0) or 0),
                reasoning_tokens=int(row.get("reasoning_tokens", 0) or 0),
                total_tokens=int(row.get("total_tokens", 0) or 0),
                estimated=False,
            ).finalize()
        else:
            usage = TokenUsage(input_tokens=estimate_tokens(prompt), output_tokens=estimate_tokens(output), estimated=True).finalize()
        self.turn.usage = usage
        self._event("token.usage", asdict(usage))

    def observe_cache(self, output: str, stable_context_digest: str | None = None) -> None:
        rows = _json_lines(output, CACHE_PREFIX)
        if rows:
            row = rows[-1]
            self.turn.cache = CacheTelemetry(
                provider_reported=True,
                hit=bool(row.get("hit")) if "hit" in row else None,
                read_tokens=int(row.get("read_tokens", 0) or 0),
                write_tokens=int(row.get("write_tokens", 0) or 0),
                cache_key=str(row.get("cache_key")) if row.get("cache_key") else None,
                source=str(row.get("source", "provider")),
            )
        elif stable_context_digest:
            self.turn.cache = CacheTelemetry(provider_reported=False, source="harness-context-only", cache_key=stable_context_digest)
        self._event("cache.telemetry", asdict(self.turn.cache))

    def decide(self, *, verification_score: float, evidence_score: float, uncertainty: float, regressions: int = 0,
               max_turns: int = 3, min_gain: float = 0.03, previous_utility: float | None = None) -> dict[str, Any]:
        self.turn.verification_score = max(0.0, min(1.0, verification_score))
        self.turn.evidence_score = max(0.0, min(1.0, evidence_score))
        self.turn.uncertainty = max(0.0, min(1.0, uncertainty))
        utility = round(0.45 * self.turn.verification_score + 0.35 * self.turn.evidence_score - 0.15 * self.turn.uncertainty - 0.10 * min(1, regressions), 4)
        token_penalty = min(0.20, self.turn.usage.total_tokens / 200000)
        utility = round(utility - token_penalty, 4)
        gain = None if previous_utility is None else round(utility - previous_utility, 4)
        if regressions:
            action, reason = "repair", "regression-detected"
        elif utility >= 0.90:
            action, reason = "stop", "quality-threshold"
        elif gain is not None and gain < min_gain:
            action, reason = "stop", "diminishing-returns"
        elif self.turn.uncertainty > 0.35:
            action, reason = "research", "uncertainty-threshold"
        elif len(self.turn.observations) == 0:
            action, reason = "stop", "no-observable-tool-work"
        else:
            action, reason = "continue", "measurable-improvement-available"
        self.turn.decision = {
            "action": action, "reason": reason, "utility": utility, "gain": gain,
            "token_penalty": round(token_penalty, 4), "max_turns": max_turns,
        }
        self._event("turn.decision", self.turn.decision)
        return self.turn.decision

    def finish(self, state: str = "completed") -> None:
        if state not in {"completed", "stopped", "failed"}:
            raise ValueError("A terminal agent turn must be completed, stopped, or failed")
        if self.turn.state not in self._allowed or state not in self._allowed[self.turn.state]:
            raise ValueError(f"Invalid terminal transition {self.turn.state} -> {state}")
        self.turn.state = state
        self._event("turn.complete", self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        value = asdict(self.turn)
        value["observations"] = [asdict(item) for item in self.turn.observations]
        return value

    def _event(self, kind: str, data: dict[str, Any]) -> None:
        record = {"turn_id": self.turn.turn_id, "phase": self.turn.phase, "event": kind, "data": data}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_provider_metadata(output: str) -> dict[str, Any]:
    """Expose structured provider protocol lines without trusting arbitrary text as telemetry."""
    return {
        "tool_observations": _json_lines(output, OBSERVATION_PREFIX),
        "usage": _json_lines(output, USAGE_PREFIX),
        "cache": _json_lines(output, CACHE_PREFIX),
    }
