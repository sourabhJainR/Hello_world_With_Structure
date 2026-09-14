"""Unified repository intelligence for AER.

This is deliberately a composition layer, not a second retrieval engine. It
reuses the existing graph-aware CodebaseIndex for semantic navigation and adds
Repomix-style repository packing: git-aware ignores, secret exclusion, token
budgets, directory structure, and optional structural compression.

Serena-inspired rule: code retrieval is symbol/relationship aware when the
index can resolve it; plain text search remains the fallback for non-code.
Repomix-inspired rule: packing is deterministic, git-aware, security-aware and
budgeted before content reaches an agent.
"""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable, Sequence

from .agency_codebase_context import CodebaseIndex, CodebaseContext, retrieve


DEFAULT_IGNORES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "coverage",
})
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*|\S")


@dataclass(frozen=True)
class PackedFile:
    path: str
    content: str
    token_estimate: int
    compressed: bool = False
    excluded_reason: str = ""


@dataclass(frozen=True)
class RepositoryPack:
    root: str
    snapshot_digest: str
    files: tuple[PackedFile, ...]
    structure: tuple[str, ...]
    token_estimate: int
    omitted: tuple[str, ...]
    security_exclusions: tuple[str, ...]

    def as_text(self) -> str:
        parts = ["<repository>", "<structure>", *self.structure, "</structure>"]
        for item in self.files:
            parts.extend([f'<file path="{item.path}">', item.content, "</file>"])
        parts.append("</repository>")
        return "\n".join(parts)


class RepositoryIntelligence:
    """Single entry point for repository context acquisition."""

    def __init__(self, root: str | Path, *, extra_ignores: Iterable[str] = ()) -> None:
        self.root = Path(root).resolve()
        self.extra_ignores = frozenset(extra_ignores)
        self.index = CodebaseIndex.build(self.root, ignores=self.ignore_names())

    def ignore_names(self) -> frozenset[str]:
        return DEFAULT_IGNORES | self.extra_ignores

    def retrieve(self, query: str, *, token_budget: int = 4000, max_files: int = 12,
                 context_lines: int = 20, graph_hops: int = 2) -> CodebaseContext:
        return retrieve(self.index, query, token_budget=token_budget, max_files=max_files,
                        context_lines=context_lines, graph_hops=graph_hops)

    def pack(self, *, include: Sequence[str] = (), ignore: Sequence[str] = (),
             token_budget: int | None = None, compress: bool = False,
             max_file_size: int = 50_000_000) -> RepositoryPack:
        patterns = tuple(include)
        ignores = tuple(ignore) + tuple(self._ignore_file_patterns())
        files: list[PackedFile] = []
        structure: list[str] = []
        omitted: list[str] = []
        security: list[str] = []
        used = 0

        candidates = []
        for current, dirs, names in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.ignore_names() and not d.startswith(".")]
            for name in names:
                path = Path(current) / name
                rel = path.relative_to(self.root).as_posix()
                structure.append(rel)
                if path.is_symlink() or path.stat().st_size > max_file_size:
                    omitted.append(rel)
                    continue
                if patterns and not any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(path.name, p) for p in patterns):
                    omitted.append(rel)
                    continue
                if any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(path.name, p) for p in ignores):
                    omitted.append(rel)
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    omitted.append(rel)
                    continue
                if self._contains_secret(text):
                    security.append(rel)
                    continue
                candidates.append((rel, text))

        for rel, text in sorted(candidates):
            payload = self._compress(text, rel) if compress else text
            count = self.token_estimate(payload)
            if token_budget is not None and used + count > token_budget:
                omitted.append(rel)
                continue
            files.append(PackedFile(rel, payload, count, compress))
            used += count

        snapshot = hashlib.sha256("\n".join(f"{p}|{hashlib.sha256(t.encode()).hexdigest()}" for p, t in candidates).encode()).hexdigest()
        return RepositoryPack(str(self.root), snapshot, tuple(files), tuple(sorted(structure)), used,
                              tuple(sorted(set(omitted))), tuple(sorted(set(security))))

    def token_estimate(self, text: str) -> int:
        return max(1, len(_TOKEN_RE.findall(text))) if text else 0

    def _ignore_file_patterns(self) -> list[str]:
        patterns: list[str] = []
        for name in (".gitignore", ".ignore", ".repomixignore"):
            path = self.root / name
            if not path.is_file():
                continue
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("!"):
                        patterns.append(line)
            except OSError:
                continue
        return patterns

    @staticmethod
    def _contains_secret(text: str) -> bool:
        return any(pattern.search(text) for pattern in _SECRET_PATTERNS)

    @staticmethod
    def _compress(text: str, path: str) -> str:
        """Keep declarations/imports/comments while dropping implementation detail."""
        suffix = Path(path).suffix.lower()
        if suffix in {".py", ".pyi"}:
            lines = text.splitlines()
            kept: list[str] = []
            indent_stack: list[int] = []
            for line in lines:
                stripped = line.strip()
                indent = len(line) - len(line.lstrip())
                if stripped.startswith(("import ", "from ", "class ", "def ", "async def ", "@", "#")):
                    kept.append(line)
                    if stripped.startswith(("class ", "def ", "async def ")):
                        indent_stack.append(indent)
                    continue
                if stripped and indent_stack and indent <= indent_stack[-1]:
                    kept.append(line)
            return "\n".join(kept)
        lines = text.splitlines()
        kept = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "#", "/*", "*", "import ", "using ", "package ")):
                kept.append(line)
            elif re.search(r"\b(class|interface|struct|enum|function|def|func)\b", line):
                kept.append(line)
        return "\n".join(kept)


__all__ = ["PackedFile", "RepositoryPack", "RepositoryIntelligence"]
