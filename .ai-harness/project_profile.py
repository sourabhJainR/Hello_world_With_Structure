#!/usr/bin/env python3
"""Detect repository conventions without introducing dependencies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _exists_any(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if (ROOT / name).exists()]


def _contains_any(paths: list[Path], needles: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        for needle in needles:
            if needle.lower() in lower:
                found.append(needle)
    return sorted(set(found))


def build_profile() -> dict[str, Any]:
    files = {p.name for p in ROOT.iterdir() if p.exists()}
    languages: list[str] = []
    if (ROOT / "pyproject.toml").exists() or (ROOT / "requirements.txt").exists() or list(ROOT.glob("*.py")):
        languages.append("python")
    if list(ROOT.glob("*.csproj")) or list(ROOT.glob("*.sln")):
        languages.append("csharp")
    if (ROOT / "package.json").exists():
        languages.append("javascript-typescript")
    if (ROOT / "go.mod").exists():
        languages.append("go")
    if (ROOT / "Cargo.toml").exists():
        languages.append("rust")
    if (ROOT / "pom.xml").exists() or (ROOT / "build.gradle").exists() or (ROOT / "build.gradle.kts").exists():
        languages.append("java-kotlin")

    manifests = _exists_any(("pyproject.toml", "requirements.txt", "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "*.csproj", "*.sln", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"))
    source_files = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and ".ai-harness" not in p.parts]
    config_sources = [p for p in source_files if p.name in {"pyproject.toml", "package.json", "requirements.txt", "Directory.Build.props", "Directory.Packages.props", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"}]

    logging_markers = _contains_any(source_files, ("serilog", "nlog", "log4net", "applicationinsights", "opentelemetry", "structlog", "logging.getlogger", "logging", "slog.", "log/slog", "slf4j", "logback", "pino", "winston"))
    test_markers = _contains_any(source_files, ("pytest", "unittest", "xunit", "nunit", "mstest", "jest", "vitest", "mocha", "junit", "testing."))
    telemetry_markers = _contains_any(source_files, ("opentelemetry", "applicationinsights", "prometheus", "datadog", "newrelic", "jaeger", "zipkin", "otel"))
    exception_markers = _contains_any(source_files, ("try:", "except", "raise", "throw new", "catch (", "panic(", "errors.new", "fmt.errorf"))
    dependency_markers = _contains_any(config_sources, ("pytest", "serilog", "nlog", "opentelemetry", "applicationinsights", "xunit", "nunit", "jest", "vitest", "junit", "pino", "winston"))

    return {
        "fresh_repository": len(source_files) == 0,
        "languages": languages,
        "manifests": manifests,
        "existing_logging_markers": logging_markers,
        "existing_test_markers": test_markers,
        "existing_telemetry_markers": telemetry_markers,
        "existing_exception_markers": exception_markers,
        "existing_dependency_markers": dependency_markers,
        "instruction_files": [name for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md") if name in files],
        "third_party_policy": ".ai-harness/DEPENDENCIES.md",
        "generated_by": "ai-coding-harness.project_profile",
    }


def main() -> int:
    print(json.dumps(build_profile(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
