#!/usr/bin/env python3
"""Controller for the bounded adaptive coding self-loop."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".ai-harness"


@dataclass
class LoopState:
    task_id: str
    cycle: int = 0
    max_cycles: int = 500
    status: str = "running"
    last_fingerprint: str = ""
    stagnant_cycles: int = 0
    blocked_cycles: int = 0
    evidence_gain: float = 0.0
    quality_score: float = 0.0
    risk_score: float = 0.0
    selected_actions: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def fingerprint(self, evidence: dict[str, Any]) -> str:
        payload = json.dumps(evidence, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class SelfLoopController:
    """Pure control logic; provider execution remains the harness responsibility."""

    def __init__(self, max_cycles: int = 500, stagnation_limit: int = 5, min_gain: float = 0.02) -> None:
        self.max_cycles = max(1, min(int(max_cycles), 500))
        self.stagnation_limit = max(2, int(stagnation_limit))
        self.min_gain = max(0.0, float(min_gain))

    def choose_actions(self, state: LoopState, evidence: dict[str, Any]) -> list[str]:
        actions: list[str] = []
        if not evidence.get("profiled"):
            actions.append("profile")
        if evidence.get("unknowns"):
            actions.append("research")
        if evidence.get("feasibility_unknown"):
            actions.append("poc")
        if evidence.get("failure_detected"):
            actions.append("debug")
        if evidence.get("new_files_needed"):
            actions.append("placement")
        if evidence.get("implementation_needed"):
            actions.append("implement")
        if evidence.get("tests_missing") or evidence.get("validation_failed"):
            actions.append("verify")
        if evidence.get("high_risk") or evidence.get("review_needed"):
            actions.append("review")
        if evidence.get("security_review"):
            actions.append("security-review")
        if evidence.get("performance_review"):
            actions.append("performance-review")
        if evidence.get("scope_drift"):
            actions.append("scope-correction")
        if not actions:
            actions.append("measure")
        return list(dict.fromkeys(actions))

    def should_stop(self, state: LoopState, evidence: dict[str, Any]) -> tuple[bool, str]:
        if evidence.get("escalation_required"):
            return True, "human-escalation"
        if evidence.get("acceptance_met") and evidence.get("verification_passed") and not evidence.get("blocking_findings"):
            if state.stagnant_cycles >= 1 or evidence.get("convergence_confident"):
                return True, "accepted-converged"
        if state.cycle >= state.max_cycles:
            return True, "cycle-limit"
        if state.stagnant_cycles >= self.stagnation_limit:
            return True, "stagnation"
        if state.blocked_cycles >= self.stagnation_limit:
            return True, "repeated-blocker"
        return False, "continue"

    def update(self, state: LoopState, evidence: dict[str, Any]) -> LoopState:
        state.cycle += 1
        quality = float(evidence.get("quality_score", state.quality_score))
        gain = max(0.0, quality - state.quality_score)
        state.evidence_gain = gain
        state.quality_score = quality
        state.risk_score = float(evidence.get("risk_score", state.risk_score))
        fp = state.fingerprint(evidence)
        if fp == state.last_fingerprint or gain < self.min_gain:
            state.stagnant_cycles += 1
        else:
            state.stagnant_cycles = 0
        if evidence.get("blocked"):
            state.blocked_cycles += 1
        else:
            state.blocked_cycles = 0
        state.last_fingerprint = fp
        state.selected_actions = self.choose_actions(state, evidence)
        state.history.append({
            "cycle": state.cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fingerprint": fp,
            "quality_score": state.quality_score,
            "evidence_gain": state.evidence_gain,
            "risk_score": state.risk_score,
            "actions": state.selected_actions,
        })
        stop, reason = self.should_stop(state, evidence)
        if stop:
            state.status = reason
        return state


def save_state(path: Path, state: LoopState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.__dict__, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptive self-loop controller")
    parser.add_argument("--task", required=True)
    parser.add_argument("--max-cycles", type=int, default=500)
    parser.add_argument("--stagnation-limit", type=int, default=5)
    parser.add_argument("--min-gain", type=float, default=0.02)
    parser.add_argument("--state-file", default=str(HARNESS / "self-loop-state.json"))
    args = parser.parse_args()
    task_id = hashlib.sha256(args.task.encode("utf-8")).hexdigest()[:12]
    state = LoopState(task_id=task_id, max_cycles=min(max(1, args.max_cycles), 500))
    controller = SelfLoopController(state.max_cycles, args.stagnation_limit, args.min_gain)
    evidence = {"profiled": False, "implementation_needed": True, "quality_score": 0.0}
    state = controller.update(state, evidence)
    save_state(Path(args.state_file), state)
    print(json.dumps({"task_id": task_id, "cycle": state.cycle, "status": state.status, "next_actions": state.selected_actions}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
