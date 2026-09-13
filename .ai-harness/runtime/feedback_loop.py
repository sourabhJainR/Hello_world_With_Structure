#!/usr/bin/env python3
"""Evidence-driven feedback loop for AER runs.

The loop records observations and produces candidates, but executable behavior
cannot be activated by the learning loop itself. Promotion requires repeated
successful observations plus regression/verification evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeedbackPolicy:
    min_observations: int = 5
    min_success_rate: float = 0.80
    min_verification_rate: float = 0.90
    min_improvement: float = 0.03


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
        candidate = {
            "candidate_id": hashlib.sha256(f"{strategy}\0{proposed_change}".encode()).hexdigest()[:16],
            "strategy": strategy, "proposed_change": proposed_change,
            "evaluation": evaluation, "active": False,
            "requires": ["deterministic_regression", "safety_gate", "shadow", "canary", "monitoring"],
        }
        return candidate
