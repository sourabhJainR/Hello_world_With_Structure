#!/usr/bin/env python3
"""Verification discovery that refuses to treat "no tests found" as proof."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _has_any(patterns: tuple[str, ...]) -> bool:
    return any((ROOT / name).exists() for name in patterns)


def discover_commands() -> list[list[str]]:
    if (ROOT / 'pyproject.toml').exists() or (ROOT / 'pytest.ini').exists() or (ROOT / 'tox.ini').exists() or (ROOT / 'setup.cfg').exists():
        if shutil.which('pytest') and any(ROOT.rglob('test_*.py')):
            return [['pytest', '-q']]
        if any(ROOT.rglob('test_*.py')) or any(ROOT.rglob('*_test.py')):
            return [['python', '-m', 'unittest', 'discover', '-v']]
        return [['python', '-m', 'compileall', '-q', '.']]
    if (ROOT / 'package.json').exists():
        return [['npm', 'test', '--if-present']]
    if (ROOT / 'go.mod').exists():
        return [['go', 'test', './...']]
    if (ROOT / 'Cargo.toml').exists():
        return [['cargo', 'test']]
    if _has_any(('.sln', '.csproj')):
        return [['dotnet', 'test', '--nologo']]
    if (ROOT / 'pom.xml').exists() and (ROOT / 'mvnw').exists():
        return [['./mvnw', 'test', '-q']]
    if (ROOT / 'pom.xml').exists() and shutil.which('mvn'):
        return [['mvn', 'test', '-q']]
    if (ROOT / 'gradlew').exists():
        return [['./gradlew', 'test']]
    if (ROOT / 'Makefile').exists():
        return [['make', 'test']]
    return []


def validate_discovery(commands: list[list[str]]) -> tuple[bool, str]:
    if not commands:
        return False, 'No deterministic validation command discovered; refusing to claim verification.'
    return True, ''
