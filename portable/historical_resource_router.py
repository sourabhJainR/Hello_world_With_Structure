from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from portable.learning_steward import LearningSteward


@dataclass(frozen=True)
class HistoricalEstimate:
    routing_key: str
    samples: int
    successful_samples: int
    failed_samples: int
    confidence: float
    duration_seconds: float
    memory_mb: int
    failure_probability: float
    evidence_yield: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "routing_key": self.routing_key,
            "samples": self.samples,
            "successful_samples": self.successful_samples,
            "failed_samples": self.failed_samples,
            "confidence": round(self.confidence, 3),
            "duration_seconds": round(self.duration_seconds, 3),
            "memory_mb": int(self.memory_mb),
            "failure_probability": round(self.failure_probability, 3),
            "evidence_yield": round(self.evidence_yield, 3),
        }


class HistoricalResourceRouter:
    """Read-only adaptive routing estimates backed by LearningSteward observations.

    The router never writes learning state and never promotes observations.
    LearningSteward remains the sole owner of durable resource observations.
    """

    def __init__(self, root: Path, *, minimum_samples: int = 2) -> None:
        self.root = Path(root)
        self.minimum_samples = max(1, int(minimum_samples))

    @staticmethod
    def routing_key(agent: Any) -> str:
        payload = {
            "role": str(agent.role),
            "command": list(agent.local_command),
            "isolation": bool(agent.local_isolation),
        }
        return "resource-route-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]

    def estimate(self, agent: Any) -> HistoricalEstimate | None:
        if not agent.local_command:
            return None
        key = self.routing_key(agent)
        rows = LearningSteward.resource_history(self.root, key, limit=50)
        if not rows:
            return None

        successes: list[Mapping[str, Any]] = []
        failures = 0
        for row in rows:
            outcome = str(row.get("outcome", "")).lower()
            if outcome == "worked":
                successes.append(row)
            elif outcome in {"failed", "regressed"}:
                failures += 1

        if not successes:
            return None

        def number(row: Mapping[str, Any], name: str, fallback: float) -> float:
            try:
                return float(row.get(name, fallback))
            except (TypeError, ValueError):
                return fallback

        durations = [number(row, "duration_seconds", agent.estimated_duration_seconds) for row in successes]
        memories = [number(row, "memory_mb", agent.estimated_memory_mb) for row in successes]
        yields = [number(row, "evidence_yield", agent.evidence_value) for row in successes]
        historical_duration = max(0.1, statistics.median(durations))
        historical_memory = max(1, int(round(statistics.median(memories))))
        historical_yield = max(0.0, min(1.0, statistics.mean(yields)))
        total = len(successes) + failures
        # Beta(1,1) smoothing keeps a sparse history conservative.
        failure_probability = (failures + 1.0) / (total + 2.0)
        confidence = min(1.0, len(successes) / float(max(self.minimum_samples, 5)))

        duration = (1.0 - confidence) * float(agent.estimated_duration_seconds) + confidence * historical_duration
        memory = (1.0 - confidence) * float(agent.estimated_memory_mb) + confidence * historical_memory
        evidence = (1.0 - confidence) * float(agent.evidence_value) + confidence * historical_yield
        return HistoricalEstimate(
            routing_key=key,
            samples=total,
            successful_samples=len(successes),
            failed_samples=failures,
            confidence=confidence,
            duration_seconds=max(0.1, duration),
            memory_mb=max(1, int(round(memory))),
            failure_probability=max(0.0, min(1.0, failure_probability)),
            evidence_yield=max(0.0, min(1.0, evidence)),
        )
