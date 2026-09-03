#!/usr/bin/env python3
"""Detect repository conventions and expose exact repository constructs to the coding workflow."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from runtime.construct_index import build_index, compact_index

ROOT = Path(__file__).resolve().parent.parent
IGNORED = {".git", ".ai-harness", ".venv", "venv", "node_modules", "bin", "obj", "dist", "build", "target"}
SOURCE_EXTENSIONS = {".py", ".cs", ".java", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"}


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


def _source_files() -> list[Path]:
    return [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in SOURCE_EXTENSIONS and not any(part in IGNORED for part in p.parts)]


def _naming_styles(files: list[Path]) -> dict[str, int]:
    counts = Counter()
    for path in files:
        stem = path.stem
        if re.fullmatch(r"[A-Z][A-Za-z0-9]*", stem):
            counts["PascalCase"] += 1
        elif re.fullmatch(r"[a-z][A-Za-z0-9]*", stem) and any(ch.isupper() for ch in stem):
            counts["camelCase"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", stem):
            counts["snake_case"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", stem):
            counts["kebab-case"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:\.[a-z0-9]+)+", stem):
            counts["dot.case"] += 1
    return dict(counts)


def _type_naming(files: list[Path]) -> dict[str, int]:
    counts = Counter()
    pattern = re.compile(r"\b(?:class|interface|struct|record|enum)\s+([A-Za-z_][A-Za-z0-9_]*)")
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name in pattern.findall(text):
            if re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
                counts["PascalCase"] += 1
            elif re.fullmatch(r"[a-z][A-Za-z0-9]*", name):
                counts["camelCase"] += 1
            elif "_" in name:
                counts["snake_case"] += 1
    return dict(counts)


def _test_locations(files: list[Path]) -> list[str]:
    tests = [p for p in files if re.search(r"(?:^|[_\.])(test|spec)(?:[_\.]|$)", p.name, re.I)]
    return sorted({str(p.parent.relative_to(ROOT)).replace("\\", "/") or "." for p in tests})[:20]


def build_profile() -> dict[str, Any]:
    root_files = {p.name for p in ROOT.iterdir() if p.is_file()}
    source_files = _source_files()
    languages: list[str] = []
    if "pyproject.toml" in root_files or "requirements.txt" in root_files or any(p.suffix == ".py" for p in source_files):
        languages.append("python")
    if any(p.suffix in {".csproj", ".sln"} for p in source_files):
        languages.append("csharp")
    if "package.json" in root_files or any(p.suffix in {".js", ".jsx", ".ts", ".tsx"} for p in source_files):
        languages.append("javascript-typescript")
    if "go.mod" in root_files:
        languages.append("go")
    if "Cargo.toml" in root_files:
        languages.append("rust")
    if "pom.xml" in root_files or "build.gradle" in root_files or "build.gradle.kts" in root_files:
        languages.append("java-kotlin")

    manifest_names = {"pyproject.toml", "requirements.txt", "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Directory.Build.props", "Directory.Packages.props"}
    manifests = sorted({p.name for p in source_files if p.name in manifest_names or p.suffix in {".csproj", ".sln"}})
    config_sources = [p for p in source_files if p.name in manifest_names or p.suffix in {".csproj", ".sln"}]

    logging_markers = _contains_any(source_files, ("serilog", "nlog", "log4net", "applicationinsights", "opentelemetry", "structlog", "logging.getlogger", "logging", "slog.", "log/slog", "slf4j", "logback", "pino", "winston"))
    test_markers = _contains_any(source_files, ("pytest", "unittest", "xunit", "nunit", "mstest", "jest", "vitest", "mocha", "junit", "testing."))
    telemetry_markers = _contains_any(source_files, ("opentelemetry", "applicationinsights", "prometheus", "datadog", "newrelic", "jaeger", "zipkin", "otel"))
    exception_markers = _contains_any(source_files, ("try:", "except", "raise", "throw new", "catch (", "panic(", "errors.new", "fmt.errorf"))
    dependency_markers = _contains_any(config_sources, ("pytest", "serilog", "nlog", "opentelemetry", "applicationinsights", "xunit", "nunit", "jest", "vitest", "junit", "pino", "winston"))

    file_naming = _naming_styles(source_files)
    type_naming = _type_naming(source_files)
    construct_index = build_index(ROOT)
    return {
        "fresh_repository": len(source_files) == 0,
        "languages": languages,
        "manifests": manifests,
        "existing_logging_markers": logging_markers,
        "existing_test_markers": test_markers,
        "existing_telemetry_markers": telemetry_markers,
        "existing_exception_markers": exception_markers,
        "existing_dependency_markers": dependency_markers,
        "naming": {
            "file_styles": file_naming,
            "dominant_file_style": max(file_naming, key=file_naming.get) if file_naming else "repository-defined",
            "type_styles": type_naming,
            "dominant_type_style": max(type_naming, key=type_naming.get) if type_naming else "language-default",
            "test_locations": _test_locations(source_files),
        },
        "instruction_files": [name for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md") if name in root_files],
        "third_party_policy": ".ai-harness/DEPENDENCIES.md",
        "construct_traceability": {
            "enabled": True,
            "schema_version": construct_index["schema_version"],
            "files_scanned": construct_index["files_scanned"],
            "construct_count": construct_index["construct_count"],
            "reference_format": "[construct-id] kind path:line::name",
            "index": compact_index(construct_index, 9000),
            "rule": "Use only constructs present in the index. If a construct cannot be resolved, mark it UNRESOLVED instead of inventing it.",
        },
        "generated_by": "ai-coding-harness.project_profile",
    }


def main() -> int:
    print(json.dumps(build_profile(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
