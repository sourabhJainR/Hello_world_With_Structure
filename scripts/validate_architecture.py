#!/usr/bin/env python3
"""Validate the AER architecture constitution without third-party dependencies.

The constitution is stored as YAML-compatible JSON so CI can validate it with
Python's standard library. This validator intentionally checks architectural
contracts and dependency direction, not every semantic property of the runtime.
Runtime-specific invariants belong in their owning module tests.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "architecture" / "architecture.yaml"

REQUIRED_PRINCIPLES = {
    "one_owner_per_concern",
    "portable_is_dependency_free",
    "learning_cannot_authorize",
    "release_requires_verification",
    "stale_evidence_requires_refresh",
    "adapters_and_views_are_not_authority",
}
ALLOWED_STATUSES = {"canonical", "adapter", "strategy", "view", "deprecated", "historical"}
FORBIDDEN_PORTABLE_IMPORT_PREFIXES = (
    "ai_harness",
    "skills",
    ".agents",
    ".claude",
    "architecture",
)


def load_contract() -> dict[str, Any]:
    if not CONTRACT.is_file():
        raise AssertionError(f"architecture contract missing: {CONTRACT}")
    try:
        raw = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"architecture contract must be YAML-compatible JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise AssertionError("architecture contract root must be an object")
    return raw


def _require(mapping: dict[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise AssertionError(f"{label} is missing required key: {key}")
    return mapping[key]


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("contract_version") != 1:
        raise AssertionError("unsupported architecture contract version")

    architecture = _require(contract, "architecture", "architecture")
    if architecture.get("short_name") != "AER":
        raise AssertionError("architecture short_name must be AER")
    if architecture.get("target_line") != "23.x":
        raise AssertionError("architecture target line must be 23.x for the consolidation slice")

    principles = set(_require(contract, "principles", "architecture contract"))
    missing = REQUIRED_PRINCIPLES - principles
    if missing:
        raise AssertionError(f"missing architecture principles: {sorted(missing)}")

    domains = _require(contract, "domains", "architecture contract")
    if not isinstance(domains, dict) or not domains:
        raise AssertionError("architecture domains must be a non-empty object")

    owners: set[str] = set()
    for name, domain in domains.items():
        if not isinstance(domain, dict):
            raise AssertionError(f"domain {name} must be an object")
        owner = _require(domain, "canonical_owner", f"domain {name}")
        if not isinstance(owner, str) or not owner.strip():
            raise AssertionError(f"domain {name} canonical_owner must be a non-empty string")
        if owner in owners:
            raise AssertionError(f"canonical owner is duplicated across domains: {owner}")
        owners.add(owner)
        compatibility = domain.get("compatibility_surfaces", [])
        if not isinstance(compatibility, list):
            raise AssertionError(f"domain {name} compatibility_surfaces must be an array")
        if owner in compatibility:
            raise AssertionError(f"domain {name} lists its canonical owner as a compatibility surface")
        if not isinstance(domain.get("rule"), str) or not domain["rule"].strip():
            raise AssertionError(f"domain {name} must declare an ownership rule")

    lifecycle = _require(contract, "lifecycle", "architecture contract")
    if lifecycle != [
        "intent", "contract", "repo_facts", "decisions", "evidence", "plan",
        "execute", "verify", "review", "regression", "release", "outcome", "learn",
    ]:
        raise AssertionError("lifecycle ordering does not match the canonical engineering spine")

    dependencies = _require(contract, "dependency_direction", "architecture contract")
    for key in ("portable", "skills", "harness", "adapters", "views"):
        if key not in dependencies or not isinstance(dependencies[key], list):
            raise AssertionError(f"dependency_direction.{key} must be an array")
    for forbidden in ("skills", "harness", "views", "adapters"):
        if forbidden in dependencies["portable"]:
            raise AssertionError(f"portable may not depend on {forbidden}")

    compatibility_policy = _require(contract, "compatibility_policy", "architecture contract")
    statuses = set(_require(compatibility_policy, "statuses", "compatibility_policy"))
    if statuses != ALLOWED_STATUSES:
        raise AssertionError("compatibility status vocabulary drifted")
    required_metadata = set(_require(compatibility_policy, "required_metadata", "compatibility_policy"))
    if required_metadata != {"status", "canonical_owner", "replacement", "removal_condition"}:
        raise AssertionError("compatibility metadata contract drifted")

    enforcement = _require(contract, "enforcement", "architecture contract")
    for key, relative in {
        "validator": "scripts/validate_architecture.py",
        "tests": "tests/test_architecture_contract.py",
        "ci": ".github/workflows/architecture-integrity.yml",
    }.items():
        if enforcement.get(key) != relative:
            raise AssertionError(f"enforcement.{key} must point to {relative}")


def _import_root(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return None


def validate_portable_import_direction() -> None:
    portable = ROOT / "portable"
    for path in sorted(portable.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            value = _import_root(node)
            if not value:
                continue
            normalized = value.lstrip(".")
            if normalized.startswith(FORBIDDEN_PORTABLE_IMPORT_PREFIXES):
                raise AssertionError(f"portable dependency direction violation in {path}: import {value!r}")


def validate_owner_metadata(contract: dict[str, Any]) -> None:
    """Ensure declared non-canonical surfaces are classified explicitly.

    A future compatibility registry can become richer without changing this
    constitution. For this first slice, the contract is the minimum authority
    and compatibility surfaces are explicitly enumerated per domain.
    """
    domains = contract["domains"]
    for name, domain in domains.items():
        owner = domain["canonical_owner"]
        if name == "learning" and owner == "portable.agency_adaptive_planning":
            rule = domain["rule"].lower()
            if "cannot grant permissions" not in rule and "cannot" not in rule:
                raise AssertionError("learning owner must explicitly remain advisory")
        if name == "architecture_views" and not domain.get("rule"):
            raise AssertionError("architecture views must remain non-authoritative")
        if owner in domain.get("compatibility_surfaces", []):
            raise AssertionError(f"domain {name} has a self-referential compatibility owner")


def validate() -> None:
    contract = load_contract()
    validate_contract(contract)
    validate_owner_metadata(contract)
    validate_portable_import_direction()


if __name__ == "__main__":
    validate()
    print(f"Architecture constitution valid: {CONTRACT.relative_to(ROOT)}")
