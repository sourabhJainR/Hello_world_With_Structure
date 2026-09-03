#!/usr/bin/env python3
"""Verification discovery that refuses to treat "no tests found" as proof."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _has_any(patterns: tuple[str, ...]) -> bool:
    return any((ROOT / name).exists() for name in patterns)


def _python_test_files() -> bool:
    tests_root = ROOT / "tests"
    if not tests_root.is_dir():
        return False
    return any(tests_root.rglob("test_*.py")) or any(tests_root.rglob("*_test.py"))


def _node_test_command() -> list[str] | None:
    package = ROOT / 'package.json'
    if not package.exists():
        return None
    try:
        data = json.loads(package.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    scripts = data.get('scripts', {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict) or not scripts.get('test'):
        return None
    if (ROOT / 'pnpm-lock.yaml').exists() and shutil.which('pnpm'):
        return ['pnpm', 'test']
    if (ROOT / 'yarn.lock').exists() and shutil.which('yarn'):
        return ['yarn', 'test']
    return ['npm', 'test']


def discover_commands() -> list[list[str]]:
    if (ROOT / 'pyproject.toml').exists() or (ROOT / 'pytest.ini').exists() or (ROOT / 'tox.ini').exists() or (ROOT / 'setup.cfg').exists():
        if shutil.which('pytest') and _python_test_files():
            return [['pytest', '-q']]
        if _python_test_files():
            return [['python', '-m', 'unittest', 'discover', '-v']]
        return [['python', '-m', 'compileall', '-q', '.']]

    # A repository may intentionally keep its Python harness dependency-free and
    # therefore have no packaging metadata. A concrete tests/ tree is still a
    # deterministic verification surface and must not be mistaken for "no tests".
    if _python_test_files():
        if shutil.which('pytest'):
            return [['pytest', '-q']]
        return [['python', '-m', 'unittest', 'discover', '-v']]

    node_test = _node_test_command()
    if node_test:
        return [node_test]
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
