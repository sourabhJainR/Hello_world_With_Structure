#!/usr/bin/env python3
"""Evidence-driven feedback loops for AER.

The learning loop remains advisory, while :class:`BoundedLoop` provides the
provider-neutral execution contract inspired by the useful parts of Forward
Future's Loopy design: fresh observation, one bounded action, acceptance
verification, evidence recording, and explicit terminal outcomes.

Execution stays behind host-supplied callbacks. This module never grants
permissions, starts schedules, or performs external side effects itself.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

LOOP_TERMINAL_STATES = (
    "success", "clean_no_op", "blocked", "approval_required",
    "exhausted", "no_progress", "error",
)


@dataclass(frozen=True)
class FeedbackPolicy:
    min_observations: int = 5
    min_success_rate: float = 0.80
    min_verification_rate: float = 0.90
    min_improvement: float = 0.03


@dataclass(frozen=True)
class LoopDefinition:
    """Immutable description of one bounded engineering loop."""
    name: str
    objective: str
    acceptance_check: str
    scope: str
    pass_limit: int
    stop_on_no_progress: bool = True
    approval_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.objective.strip():
            raise ValueError("loop name and objective are required")
        if not self.acceptance_check.strip():
            raise ValueError("acceptance_check is required")
        if not self.scope.strip():
            raise ValueError("scope is required")
        if self.pass_limit < 1:
            raise ValueError("pass_limit must be at least 1")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "objective": self.objective,
            "acceptance_check": self.acceptance_check,
            "scope": self.scope,
            "pass_limit": self.pass_limit,
            "stop_on_no_progress": self.stop_on_no_progress,
            "approval_actions": list(self.approval_actions),
        }

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LoopAction:
    """Host-selected action for one pass."""
    description: str
    evidence: tuple[str, ...] = ()
    requires_approval: bool = False


@dataclass(frozen=True)
class VerificationResult:
    """Verification result returned by the host after an action."""
    passed: bool
    complete: bool = False
    progress: bool = False
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoopPass:
    number: int
    observation: str
    action: str
    evidence: tuple[str, ...]
    verified: bool
    progress: bool
    complete: bool = False
    next_action: str = ""
    approval_required: bool = False
    error: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "number": self.number,
            "observation": self.observation,
            "action": self.action,
            "evidence": list(self.evidence),
            "verified": self.verified,
            "progress": self.progress,
            "complete": self.complete,
            "next_action": self.next_action,
            "approval_required": self.approval_required,
            "error": self.error,
        }


@dataclass(frozen=True)
class LoopRunReceipt:
    """Compact, replayable result of one bounded loop execution."""
    definition_digest: str
    loop_name: str
    scope: str
    acceptance_check: str
    boundary: str
    result: str
    passes: tuple[LoopPass, ...] = field(default_factory=tuple)
    next_step: str = ""
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        if self.result not in LOOP_TERMINAL_STATES:
            raise ValueError(f"unsupported loop result: {self.result}")
        if not self.definition_digest:
            raise ValueError("definition_digest is required")
        if not self.boundary.strip():
            raise ValueError("boundary is required")
        if not self.receipt_digest:
            payload = json.dumps(self._unsigned_dict(), sort_keys=True, separators=(",", ":"))
            object.__setattr__(self, "receipt_digest", hashlib.sha256(payload.encode("utf-8")).hexdigest())

    def _unsigned_dict(self) -> dict[str, object]:
        return {
            "definition_digest": self.definition_digest,
            "loop_name": self.loop_name,
            "scope": self.scope,
            "acceptance_check": self.acceptance_check,
            "boundary": self.boundary,
            "result": self.result,
            "passes": [item.as_dict() for item in self.passes],
            "next_step": self.next_step,
        }

    def as_dict(self) -> dict[str, object]:
        value = self._unsigned_dict()
        value["receipt_digest"] = self.receipt_digest
        return value


Observe = Callable[[int], str]
Choose = Callable[[str, int], LoopAction | None]
Act = Callable[[LoopAction, int], None]
Verify = Callable[[LoopAction, int], VerificationResult | bool | tuple[bool, Sequence[str]]]


class BoundedLoop:
    """Run a loop with explicit boundaries and fail-closed terminal states."""

    def __init__(self, definition: LoopDefinition) -> None:
        self.definition = definition

    @staticmethod
    def _normalize_verification(value: VerificationResult | bool | tuple[bool, Sequence[str]]) -> VerificationResult:
        if isinstance(value, VerificationResult):
            return value
        if isinstance(value, tuple):
            passed, evidence = value
            return VerificationResult(
                passed=bool(passed), progress=bool(passed), evidence=tuple(str(item) for item in evidence)
            )
        return VerificationResult(passed=bool(value), progress=bool(value))

    def _receipt(self, *, result: str, passes: list[LoopPass], next_step: str) -> LoopRunReceipt:
        return LoopRunReceipt(
            definition_digest=self.definition.digest(),
            loop_name=self.definition.name,
            scope=self.definition.scope,
            acceptance_check=self.definition.acceptance_check,
            boundary=f"max_passes={self.definition.pass_limit}",
            result=result,
            passes=tuple(passes),
            next_step=next_step,
        )

    def run(self, *, observe: Observe, choose: Choose, act: Act, verify: Verify) -> LoopRunReceipt:
        passes: list[LoopPass] = []
        for number in range(1, self.definition.pass_limit + 1):
            try:
                observation = str(observe(number))
                action = choose(observation, number)
                if action is None:
                    return self._receipt(
                        result="clean_no_op",
                        passes=passes,
                        next_step="nothing; the scoped work is already complete or no safe action is available",
                    )
                if action.requires_approval or action.description in self.definition.approval_actions:
                    passes.append(
                        LoopPass(number, observation, action.description, action.evidence, False, False, approval_required=True)
                    )
                    return self._receipt(
                        result="approval_required",
                        passes=passes,
                        next_step=f"approve the exact action before continuing: {action.description}",
                    )

                act(action, number)
                verification = self._normalize_verification(verify(action, number))
                passes.append(
                    LoopPass(
                        number=number,
                        observation=observation,
                        action=action.description,
                        evidence=verification.evidence or action.evidence,
                        verified=verification.passed,
                        progress=verification.progress,
                        complete=verification.complete,
                    )
                )
                if not verification.passed:
                    return self._receipt(
                        result="blocked",
                        passes=passes,
                        next_step="verification failed; inspect the evidence before another pass",
                    )
                if verification.complete:
                    return self._receipt(
                        result="success",
                        passes=passes,
                        next_step="acceptance criteria met",
                    )
                if not verification.progress and self.definition.stop_on_no_progress:
                    return self._receipt(
                        result="no_progress",
                        passes=passes,
                        next_step="no measurable progress after the latest verified action",
                    )
            except Exception as exc:
                passes.append(
                    LoopPass(
                        number=number, observation="", action="", evidence=(), verified=False,
                        progress=False, error=f"{type(exc).__name__}: {exc}",
                    )
                )
                return self._receipt(
                    result="error",
                    passes=passes,
                    next_step="inspect the execution error and resume only after the blocker is understood",
                )

        return self._receipt(
            result="exhausted",
            passes=passes,
            next_step="run boundary exhausted; review remaining work before another explicit run",
        )


class FeedbackLoop:
    def __init__(self, root: Path, policy: FeedbackPolicy | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self.policy = policy or FeedbackPolicy()
        self.path = self.root / ".ai-harness" / "learning" / "feedback-events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def observe(self, *, task_id: str, outcome: str, verified: bool, strategy: str, evidence: list[str] | None = None) -> dict:
        event = {
            "ts": time.time(), "task_id": task_id, "outcome": outcome,
            "verified": bool(verified), "strategy": strategy,
            "evidence": list(evidence or []),
        }
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event["event_digest"] = hashlib.sha256(payload.encode()).hexdigest()[:16]
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def evaluate(self, *, strategy: str) -> dict:
        events: list[dict] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines()[-500:]:
                try:
                    value = json.loads(line)
                    if value.get("strategy") == strategy:
                        events.append(value)
                except json.JSONDecodeError:
                    continue
        n = len(events)
        successes = sum(1 for e in events if e.get("outcome") in {"success", "passed"})
        verified = sum(1 for e in events if e.get("verified"))
        success_rate = successes / n if n else 0.0
        verification_rate = verified / n if n else 0.0
        eligible = n >= self.policy.min_observations and success_rate >= self.policy.min_success_rate and verification_rate >= self.policy.min_verification_rate
        return {
            "strategy": strategy, "observations": n, "success_rate": round(success_rate, 4),
            "verification_rate": round(verification_rate, 4), "candidate_eligible": eligible,
            "activation": "blocked_until_regression_and_safety_gates" if eligible else "insufficient_evidence",
        }

    def candidate(self, *, strategy: str, proposed_change: str) -> dict:
        evaluation = self.evaluate(strategy=strategy)
        return {
            "candidate_id": hashlib.sha256(f"{strategy}\0{proposed_change}".encode()).hexdigest()[:16],
            "strategy": strategy, "proposed_change": proposed_change,
            "evaluation": evaluation, "active": False,
            "requires": ["deterministic_regression", "safety_gate", "shadow", "canary", "monitoring"],
        }
