#!/usr/bin/env python3
"""AER provider conformance harness.

Runs deterministic contract checks for Claude, Codex, Gemini and ChatGPT and,
when explicitly requested, lightweight live probes against installed providers.
The harness never treats provider availability as a passing execution result.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / ".ai-harness" / "PROVIDER_MATRIX.json"
REPORT = ROOT / ".ai-harness" / "provider-conformance.json"


@dataclass
class Check:
    id: str
    status: str
    detail: str
    evidence: dict[str, Any]


@dataclass
class ProviderResult:
    provider: str
    surface: str
    mode: str
    status: str
    checks: list[Check]


def load_matrix() -> dict[str, Any]:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def command_available(provider: str) -> bool:
    executable = {"claude": "claude", "codex": "codex", "gemini": "gemini"}.get(provider)
    return bool(executable and shutil.which(executable))


def native_surface_checks(provider: str, spec: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    instruction_files = [ROOT / p for p in spec.get("instruction_files", [])]
    existing = [str(p.relative_to(ROOT)) for p in instruction_files if p.exists()]
    checks.append(Check(
        "instruction-surface",
        "pass" if existing else "fail",
        "native instruction surface is discoverable" if existing else "no native instruction surface found",
        {"expected": spec.get("instruction_files", []), "existing": existing},
    ))
    if provider == "chatgpt":
        checks.append(Check(
            "execution-transport",
            "pass",
            "ChatGPT is modeled as MCP/app or Codex-in-ChatGPT, not a local subprocess",
            {"transport": spec.get("execution_transport")},
        ))
    else:
        checks.append(Check(
            "local-transport",
            "pass" if spec.get("supports_local_execution") else "fail",
            "provider declares an explicit local execution transport",
            {"command_template": spec.get("command_template")},
        ))
    checks.append(Check(
        "jit-context",
        "pass" if spec.get("native_context_is_jit") else "info",
        "provider JIT context behavior recorded",
        {"native_context_is_jit": spec.get("native_context_is_jit")},
    ))
    return checks


def contract_checks(matrix: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    providers = matrix.get("providers", {})
    required = {"claude", "codex", "gemini", "chatgpt"}
    missing = sorted(required - set(providers))
    checks.append(Check(
        "provider-coverage",
        "pass" if not missing else "fail",
        "all required logical providers are represented" if not missing else "provider missing from matrix",
        {"required": sorted(required), "missing": missing},
    ))
    required_fields = ["surfaces", "instruction_files", "optional_mechanisms"]
    for provider, spec in providers.items():
        absent = [field for field in required_fields if not spec.get(field)]
        checks.append(Check(
            f"schema-{provider}",
            "pass" if not absent else "fail",
            "provider capability declaration is complete" if not absent else "provider declaration is incomplete",
            {"missing": absent},
        ))
    normalized = matrix.get("normalized_contract", [])
    expected = {"intent_digest", "goal", "boundaries", "acceptance", "risk", "capability_plan", "context_lease_digests", "tool_observations", "verification_evidence", "outcome"}
    missing = sorted(expected - set(normalized))
    checks.append(Check(
        "normalized-contract",
        "pass" if not missing else "fail",
        "normalized contract contains required cross-provider evidence" if not missing else "normalized contract is incomplete",
        {"missing": missing},
    ))
    return checks


def live_probe(provider: str) -> Check:
    executable = {"claude": "claude", "codex": "codex", "gemini": "gemini"}.get(provider)
    if not executable:
        return Check("live-probe", "unsupported", "no local subprocess is defined for this surface", {})
    path = shutil.which(executable)
    if not path:
        return Check("live-probe", "unavailable", f"{executable} executable is not installed", {"executable": executable})
    prompt = "Reply with exactly AER_CONFORMANCE_OK and nothing else. Do not modify files."
    if provider == "claude":
        command = [executable, "-p", prompt]
    elif provider == "codex":
        command = [executable, "exec", "--sandbox", "read-only", prompt]
    else:
        command = [executable, "-p", prompt]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            env={**os.environ, "AER_CONFORMANCE_PROBE": "1"},
        )
    except subprocess.TimeoutExpired:
        return Check("live-probe", "timeout", "provider did not complete the read-only probe within 30 seconds", {"duration_ms": 30000})
    duration_ms = round((time.monotonic() - started) * 1000)
    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        return Check("live-probe", "fail", "provider returned a non-zero exit status", {"returncode": completed.returncode, "duration_ms": duration_ms})
    return Check(
        "live-probe",
        "pass" if output == "AER_CONFORMANCE_OK" else "fail",
        "provider returned the exact conformance sentinel" if output == "AER_CONFORMANCE_OK" else "provider output did not match the sentinel",
        {"returncode": completed.returncode, "duration_ms": duration_ms, "output_digest": __import__("hashlib").sha256(output.encode()).hexdigest()},
    )


def run(live: bool = False) -> dict[str, Any]:
    matrix = load_matrix()
    all_checks = contract_checks(matrix)
    providers: list[ProviderResult] = []
    for provider, spec in matrix["providers"].items():
        checks = native_surface_checks(provider, spec)
        if live:
            checks.append(live_probe(provider))
        status = "pass" if all(c.status in {"pass", "info", "unsupported", "unavailable"} for c in checks) and not any(c.status == "fail" for c in checks) else "fail"
        providers.append(ProviderResult(provider, spec["surfaces"][0], "live" if live else "static", status, checks))
    static_pass = not any(c.status == "fail" for c in all_checks)
    report = {
        "schema_version": 1,
        "generated_at": time.time(),
        "mode": "live" if live else "static",
        "static_contract": {"status": "pass" if static_pass else "fail", "checks": [asdict(c) for c in all_checks]},
        "providers": [asdict(p) for p in providers],
        "release_ready": static_pass and all(p.status == "pass" for p in providers),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AER cross-provider conformance checks")
    parser.add_argument("--live", action="store_true", help="run read-only probes against locally installed providers")
    parser.add_argument("--json", action="store_true", help="emit machine-readable report")
    args = parser.parse_args()
    report = run(live=args.live)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Provider conformance ({report['mode']}):")
        print(f"- static contract: {report['static_contract']['status']}")
        for provider in report["providers"]:
            print(f"- {provider['provider']}: {provider['status']}")
            for check in provider["checks"]:
                print(f"  {check['status'].upper():11} {check['id']}: {check['detail']}")
        print("RELEASE READY" if report["release_ready"] else "NOT RELEASE READY")
    return 0 if report["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
