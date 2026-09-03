#!/usr/bin/env python3
"""Deterministic artifact chain for AI-native SDLC runs.

The chain keeps human intent stable while deriving machine-actionable specification
and execution planning artifacts. These files are run-scoped evidence, not authority
that can override repository policy or human approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VERSION = "1.0"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _bullets(values: list[str], fallback: str) -> str:
    if not values:
        return f"- {fallback}"
    return "\n".join(f"- {value}" for value in values)


def build_artifacts(run_dir: Path, contract: dict[str, Any], *, route: dict[str, Any]) -> dict[str, Any]:
    """Create intent.md, spec.md and plan.md and return their metadata."""
    goal = str(contract.get("goal", "")).strip()
    if not goal:
        raise ValueError("artifact chain requires a non-empty intent goal")
    digest = str(contract.get("intent_digest") or _digest(contract))
    intent = f"""# Intent\n\n> Immutable source of truth for this run. Digest: `{digest}`\n\n## Goal\n{goal}\n\n## Why\n{_bullets(contract.get('requirements', []), 'Preserve the intent and solve the stated problem without broadening scope.')}\n\n## Requirements\n{_bullets(contract.get('requirements', []), 'No additional requirements were supplied.')}\n\n## Acceptance criteria\n{_bullets(contract.get('acceptance', []), 'Required deterministic verification and evidence must pass before completion.')}\n\n## Guardrails\n{_bullets(contract.get('constraints', []) + contract.get('protected_behavior', []), 'Preserve security, compatibility, repository policy, and protected behavior.')}\n\n## Boundaries\n{_bullets(contract.get('boundaries', []), 'Repository-local scope only.')}\n\n## Non-goals\n{_bullets(contract.get('non_goals', []), 'Do not expand into adjacent improvements.')}\n"""

    spec = f"""# Specification\n\nDerived from immutable intent `{digest}`. This is a machine-actionable working specification; it cannot override intent, repository policy, security controls, or approval requirements.\n\n## Objective\n{goal}\n\n## Functional requirements\n{_bullets(contract.get('requirements', []), 'Implement the minimum behavior necessary to satisfy the goal.')}\n\n## Acceptance\n{_bullets(contract.get('acceptance', []), 'Run deterministic validation and record evidence.')}\n\n## Constraints and protected behavior\n{_bullets(contract.get('constraints', []) + contract.get('protected_behavior', []), 'No known exceptions.')}\n\n## Scope boundary\n{_bullets(contract.get('boundaries', []), 'Repository scope.')}\n"""

    plan = f"""# Plan\n\nPlan for intent `{digest}`. The execution agent may refine sequencing when repository evidence requires it, but must not change the goal, acceptance criteria, guardrails, or non-goals silently.\n\n## Route\n```json\n{json.dumps(route, ensure_ascii=False, indent=2, sort_keys=True)}\n```\n\n## Execution sequence\n1. Inspect repository conventions, relevant code, tests, and dependencies.\n2. Identify the smallest change surface and affected behavior.\n3. Implement the smallest independently verifiable chunk.\n4. Run deterministic validation and capture evidence.\n5. Review the final diff against intent, specification, and acceptance criteria.\n6. Stop when the exit criteria are satisfied. Do not expand into adjacent improvements; record deferred findings separately.\n\n## Completion gate\nNo completion claim without required verification, acceptance evidence, scope/diff evidence, and an auditable outcome.\n"""

    files = {"intent.md": intent, "spec.md": spec, "plan.md": plan}
    metadata: dict[str, Any] = {"version": VERSION, "intent_digest": digest, "artifacts": {}}
    for name, content in files.items():
        path = run_dir / name
        path.write_text(content, encoding="utf-8")
        metadata["artifacts"][name] = {
            "path": str(path),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
    (run_dir / "artifact-chain.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata
