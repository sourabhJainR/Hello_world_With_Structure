#!/usr/bin/env python3
"""Deterministic language/runtime/toolchain compatibility profile for target repositories."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _version(value: str) -> str | None:
    match = re.search(r"(?:^|[^0-9])([0-9]+(?:\.[0-9]+){0,3})(?:[^0-9]|$)", value)
    return match.group(1) if match else None


def build_compatibility_profile(root: Path = ROOT) -> dict[str, Any]:
    evidence: list[dict[str, str]] = []
    constraints: list[str] = []

    def add(language: str, source: str, version: str | None, kind: str) -> None:
        if version:
            evidence.append({"language": language, "source": source, "version": version, "kind": kind})

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = _read(pyproject)
        match = re.search(r"requires-python\s*=\s*[\"']([^\"']+)", text, re.I)
        add("python", "pyproject.toml", _version(match.group(1)) if match else None, "declared")
    for name in (".python-version", "runtime.txt"):
        path = root / name
        if path.exists():
            add("python", name, _version(_read(path)), "runtime")

    package = root / "package.json"
    if package.exists():
        try:
            value = json.loads(_read(package))
            engines = value.get("engines", {}) if isinstance(value, dict) else {}
            add("node", "package.json", _version(str(engines.get("node", ""))), "declared")
            add("npm", "package.json", _version(str(engines.get("npm", ""))), "declared")
        except json.JSONDecodeError:
            constraints.append("package.json could not be parsed; version is UNRESOLVED VERSION")
    for name in (".nvmrc", ".node-version"):
        path = root / name
        if path.exists():
            add("node", name, _version(_read(path)), "runtime")

    for path in sorted(root.glob("*.csproj")) + sorted(root.glob("*.fsproj")) + sorted(root.glob("*.vbproj")):
        text = _read(path)
        match = re.search(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>", text, re.I)
        if match:
            add("dotnet", path.name, _version(match.group(1)), "target-framework")
        match = re.search(r"<LangVersion>([^<]+)</LangVersion>", text, re.I)
        if match:
            add("csharp", path.name, match.group(1).strip(), "language")
    for name in ("global.json", "Directory.Build.props"):
        path = root / name
        if path.exists():
            text = _read(path)
            match = re.search(r'"version"\s*:\s*"([0-9.]+)"', text) if name == "global.json" else re.search(r"<LangVersion>([^<]+)</LangVersion>", text, re.I)
            if match:
                add("dotnet" if name == "global.json" else "csharp", name, match.group(1).strip(), "toolchain")

    go = root / "go.mod"
    if go.exists():
        match = re.search(r"^go\s+([0-9.]+)", _read(go), re.M)
        add("go", "go.mod", match.group(1) if match else None, "language")

    cargo = root / "Cargo.toml"
    if cargo.exists():
        text = _read(cargo)
        match = re.search(r"rust-version\s*=\s*[\"']([^\"']+)", text)
        add("rust", "Cargo.toml", _version(match.group(1)) if match else None, "language")
    rust_toolchain = root / "rust-toolchain.toml"
    if rust_toolchain.exists():
        match = re.search(r"channel\s*=\s*[\"']([^\"']+)", _read(rust_toolchain))
        add("rust", "rust-toolchain.toml", _version(match.group(1)) if match else None, "toolchain")

    pom = root / "pom.xml"
    if pom.exists():
        text = _read(pom)
        for tag in ("maven.compiler.release", "maven.compiler.source", "java.version"):
            match = re.search(rf"<{re.escape(tag)}>([^<]+)</{re.escape(tag)}>", text, re.I)
            if match:
                add("java", "pom.xml", _version(match.group(1)), "language")
                break
    for path in (root / "build.gradle", root / "build.gradle.kts"):
        if path.exists():
            match = re.search(r"(?:sourceCompatibility|jvmToolchain|JavaVersion\.VERSION_)[^\n]*?([0-9]{1,2}(?:\.[0-9]+)?)", _read(path), re.I)
            if match:
                add("java", path.name, _version(match.group(1)), "language")

    composer = root / "composer.json"
    if composer.exists():
        try:
            value = json.loads(_read(composer))
            require = value.get("require", {}) if isinstance(value, dict) else {}
            add("php", "composer.json", _version(str(require.get("php", ""))), "declared")
        except json.JSONDecodeError:
            constraints.append("composer.json could not be parsed; PHP version is UNRESOLVED VERSION")

    gemfile = root / "Gemfile"
    if gemfile.exists():
        text = _read(gemfile)
        match = re.search(r"ruby\s+[\"']([^\"']+)", text, re.I)
        add("ruby", "Gemfile", _version(match.group(1)) if match else None, "declared")
    for name in (".ruby-version", ".tool-versions"):
        path = root / name
        if path.exists():
            text = _read(path)
            match = re.search(r"ruby\s+([0-9.]+)", text) if name == ".tool-versions" else re.search(r"([0-9]+(?:\.[0-9]+){1,2})", text)
            add("ruby", name, match.group(1) if match else None, "runtime")

    evidence.sort(key=lambda item: (item["language"], item["source"], item["kind"]))
    return {
        "schema_version": 1,
        "languages": sorted({item["language"] for item in evidence}),
        "evidence": evidence,
        "constraints": constraints,
        "policy": {
            "preserve_declared_versions": True,
            "upgrade_requires_explicit_task": True,
            "unknown_version_marker": "UNRESOLVED VERSION",
            "legacy_mode": True,
        },
    }


def compatibility_instructions(profile: dict[str, Any]) -> str:
    lines = ["## Legacy compatibility contract", "Treat detected language/runtime/toolchain versions as compatibility boundaries."]
    if profile.get("evidence"):
        for item in profile["evidence"]:
            lines.append(f"- PRESERVE {item['language']} {item['version']} from {item['source']} ({item['kind']})")
    else:
        lines.append("- UNRESOLVED VERSION: do not assume a modern language/runtime version.")
    lines.extend([
        "- Do not introduce syntax, APIs, standard-library features, compiler flags, package versions, or framework APIs unavailable to the detected target.",
        "- Prefer the repository's existing compiler/runtime/package-manager commands and lockfiles.",
        "- If compatibility cannot be established, mark the version UNRESOLVED VERSION and verify before changing implementation strategy.",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(build_compatibility_profile(), indent=2, ensure_ascii=False))
