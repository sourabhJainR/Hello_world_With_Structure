#!/usr/bin/env python3
"""Versioned, auditable AER policy registry with rollback support."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable
import json
import time


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    version: int
    task_class: str
    strategy: str
    status: str = "candidate"
    confidence: float = 0.0
    promoted_at: int | None = None
    retired_at: int | None = None


class PolicyRegistry:
    def __init__(self, policies: Iterable[Policy] = ()) -> None:
        self._policies: dict[tuple[str, int], Policy] = {(p.policy_id, p.version): p for p in policies}

    def add_candidate(self, policy: Policy) -> Policy:
        if policy.status != "candidate":
            raise ValueError("new policies must start as candidate")
        self._policies[(policy.policy_id, policy.version)] = policy
        return policy

    def promote(self, policy_id: str, version: int, *, now: int | None = None) -> Policy:
        key = (policy_id, version)
        policy = self._policies[key]
        if policy.status != "candidate":
            raise ValueError("only candidates can be promoted")
        promoted = Policy(**{**asdict(policy), "status": "active", "promoted_at": int(time.time()) if now is None else now})
        self._policies[key] = promoted
        return promoted

    def rollback(self, policy_id: str, version: int, *, now: int | None = None) -> Policy:
        key = (policy_id, version)
        policy = self._policies[key]
        if policy.status != "active":
            raise ValueError("only active policies can be rolled back")
        retired = Policy(**{**asdict(policy), "status": "rolled_back", "retired_at": int(time.time()) if now is None else now})
        self._policies[key] = retired
        return retired

    def active(self, task_class: str) -> list[Policy]:
        return sorted((p for p in self._policies.values() if p.status == "active" and p.task_class == task_class), key=lambda p: (p.confidence, p.version), reverse=True)

    def export_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(p), sort_keys=True) for p in self._policies.values())
