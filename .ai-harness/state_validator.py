#!/usr/bin/env python3
"""Dependency-free validator for the portable Engineering State Ledger."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED = {
    "schema_version", "task_id", "status", "intent", "contract", "repo_facts",
    "decisions", "evidence", "changeset", "verification", "outcome", "open_risks", "next",
}
STATUSES = {
    "intake", "grilling", "specified", "investigating", "planned", "implementing",
    "verifying", "reviewing", "completed", "blocked", "cancelled",
}
OUTCOMES = {"accepted", "rejected", "partial", "unknown"}
VERIFICATION = {"passed", "failed", "skipped", "unknown"}
EVIDENCE_KINDS = {"source", "test", "runtime", "history", "documentation", "external", "tool"}


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def validate_state(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be an object"]
    missing = REQUIRED - set(state)
    errors.extend(f"missing required field: {key}" for key in sorted(missing))
    if state.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if not isinstance(state.get("task_id"), str) or not state.get("task_id"):
        errors.append("task_id must be a non-empty string")
    if state.get("status") not in STATUSES:
        errors.append("invalid status")

    intent = state.get("intent")
    if not isinstance(intent, dict) or not isinstance(intent.get("goal"), str):
        errors.append("intent.goal must be a string")
    contract = state.get("contract")
    if not isinstance(contract, dict):
        errors.append("contract must be an object")
    else:
        for key in ("requirements", "acceptance", "protected_behavior"):
            if not isinstance(contract.get(key), list):
                errors.append(f"contract.{key} must be an array")
    for key in ("repo_facts", "decisions", "evidence", "verification", "open_risks", "next"):
        if not isinstance(state.get(key), list):
            errors.append(f"{key} must be an array")

    evidence = state.get("evidence", [])
    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"evidence[{index}] must be an object")
                continue
            for key in ("id", "kind", "source", "claim", "confidence"):
                if key not in item:
                    errors.append(f"evidence[{index}] missing {key}")
            if item.get("kind") not in EVIDENCE_KINDS:
                errors.append(f"evidence[{index}].kind invalid")
            if item.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"evidence[{index}].confidence invalid")

    verification = state.get("verification", [])
    if isinstance(verification, list):
        for index, item in enumerate(verification):
            if not isinstance(item, dict) or item.get("status") not in VERIFICATION:
                errors.append(f"verification[{index}] invalid")

    outcome = state.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("status") not in OUTCOMES:
        errors.append("outcome.status invalid")
    if not isinstance(state.get("changeset"), dict):
        errors.append("changeset must be an object")
    if not _is_str_list(state.get("next")):
        errors.append("next must be an array of strings")
    return errors


def validate_file(path: Path) -> tuple[bool, list[str]]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [str(exc)]
    errors = validate_state(state)
    return not errors, errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    ok, errors = validate_file(args.path)
    if not ok:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Engineering State Ledger: valid")
