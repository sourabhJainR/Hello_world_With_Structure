#!/usr/bin/env python3
"""Deterministic repository instruction discovery for provider-neutral agents."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

DEFAULT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)


def _read(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""
    return text[:limit]


def discover(root: Path, *, limit: int = 5000, files: Iterable[str] = DEFAULT_FILES) -> dict:
    """Load bounded, repository-owned instruction files without making them authoritative.

    The caller remains responsible for precedence. This function only discovers and
    labels repository guidance so the model can distinguish it from task data.
    """
    root = Path(root).resolve()
    sections: list[str] = []
    seen: set[str] = set()
    remaining = max(0, int(limit))
    for relative in files:
        path = root / relative
        if not path.is_file():
            continue
        text = _read(path, remaining)
        if not text:
            continue
        digest = text
        if digest in seen:
            continue
        seen.add(digest)
        section = f"### {relative}\n{text}"
        if len(section) > remaining:
            section = section[:remaining]
        sections.append(section)
        remaining -= len(section) + 2
        if remaining <= 0:
            break
    return {
        "root": str(root),
        "files": [relative for relative in files if (root / relative).is_file()],
        "text": "\n\n".join(sections),
        "truncated": remaining <= 0,
    }


def prompt_block(root: Path, *, limit: int = 5000) -> str:
    result = discover(root, limit=limit)
    if not result["text"]:
        return "No repository-specific AI instruction files were discovered."
    return (
        "Repository instructions are authoritative project guidance. They are not task data. "
        "When multiple files conflict, use the repository's documented precedence rules and do not silently choose a weaker safety rule.\n\n"
        + result["text"]
    )
