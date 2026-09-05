#!/usr/bin/env python3
"""Versioned, auditable policy registry with atomic promotion and rollback lineage."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    version: int
    task_class: str
    strategy: str
    status: str = "candidate"
    confidence: float = 0.0
    score: float = 0.0
    parent_policy_id: str = ""
    evidence_hash: str = ""
    promoted_at: int | None = None
    retired_at: int | None = None
    rollout_stage: int = 0


class PolicyRegistry:
    def __init__(self, policies: Iterable[Policy] = ()) -> None:
        self._policies: dict[tuple[str, int], Policy] = {(p.policy_id, p.version): p for p in policies}

    @classmethod
    def from_jsonl(cls, text: str) -> "PolicyRegistry":
        policies: list[Policy] = []
        for line in text.splitlines():
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    continue
                # Backward-compatible defaults for pre-v2 registry rows.
                fields = asdict(Policy("", 0, "", ""))
                fields.update(row)
                policies.append(Policy(**fields))
            except (json.JSONDecodeError, TypeError):
                continue
        return cls(policies)

    def add_candidate(self, policy: Policy) -> Policy:
        if policy.status != "candidate":
            raise ValueError("new policies must start as candidate")
        key = (policy.policy_id, policy.version)
        if key in self._policies:
            return self._policies[key]
        self._policies[key] = policy
        return policy

    def next_version(self, task_class: str) -> int:
        versions = [p.version for p in self._policies.values() if p.task_class == task_class]
        return max(versions, default=0) + 1

    def current(self, task_class: str) -> Policy | None:
        active = self.active(task_class)
        return active[0] if active else None

    def promote(self, policy_id: str, version: int, *, now: int | None = None) -> Policy:
        key = (policy_id, version)
        if key not in self._policies:
            raise KeyError(f"unknown policy: {policy_id}@{version}")
        policy = self._policies[key]
        if policy.status != "candidate":
            raise ValueError("only candidates can be promoted")
        timestamp = int(time.time()) if now is None else int(now)
        current = self.current(policy.task_class)
        parent_id = policy.parent_policy_id or (current.policy_id if current else "")
        for old_key, old in list(self._policies.items()):
            if old.task_class == policy.task_class and old.status == "active":
                self._policies[old_key] = Policy(**{**asdict(old), "status": "superseded", "retired_at": timestamp, "rollout_stage": 0})
        promoted = Policy(**{**asdict(policy), "status": "active", "parent_policy_id": parent_id,
                             "promoted_at": timestamp, "retired_at": None, "rollout_stage": 5})
        self._policies[key] = promoted
        return promoted

    def active_for_id(self, policy_id: str) -> Policy | None:
        active = [p for p in self._policies.values() if p.policy_id == policy_id and p.status == "active"]
        return max(active, key=lambda p: p.version, default=None)

    def rollback(self, policy_id: str, version: int, *, now: int | None = None, restore_previous: bool = True) -> Policy:
        key = (policy_id, version)
        policy = self._policies[key]
        if policy.status != "active":
            raise ValueError("only active policies can be rolled back")
        timestamp = int(time.time()) if now is None else int(now)
        retired = Policy(**{**asdict(policy), "status": "rolled_back", "retired_at": timestamp, "rollout_stage": 0})
        self._policies[key] = retired
        if restore_previous:
            prior = [p for p in self._policies.values()
                     if p.task_class == policy.task_class and p.status == "superseded" and p.version < policy.version]
            if prior:
                previous = max(prior, key=lambda p: (p.version, p.confidence))
                self._policies[(previous.policy_id, previous.version)] = Policy(
                    **{**asdict(previous), "status": "active", "retired_at": None, "rollout_stage": 5}
                )
        return retired

    def active(self, task_class: str) -> list[Policy]:
        return sorted((p for p in self._policies.values() if p.status == "active" and p.task_class == task_class),
                      key=lambda p: (p.confidence, p.version), reverse=True)

    def best_strategy(self, task_class: str) -> str | None:
        active = self.active(task_class)
        return active[0].strategy if active else None

    def export_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(p), sort_keys=True) for p in sorted(self._policies.values(), key=lambda p: (p.task_class, p.version, p.policy_id)))
