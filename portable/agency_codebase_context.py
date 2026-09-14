"""Efficient, evidence-first codebase retrieval for coding agents.

The retriever builds a lightweight repository map once, ranks paths before reading
large files, extracts only relevant symbol windows, and reports explicit unknowns.
It is dependency-free and deterministic so a host can cache the snapshot safely.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ast
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable, Sequence


DEFAULT_IGNORES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "coverage",
})
TEXT_EXTENSIONS = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs",
    ".cpp", ".cc", ".h", ".hpp", ".c", ".sql", ".sh", ".ps1", ".md", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".txt", ".proto",
})
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    path: str
    line: int


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str
    lines: int
    symbols: tuple[Symbol, ...] = ()
    imports: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextChunk:
    path: str
    start_line: int
    end_line: int
    text: str
    score: float
    reason: str

    @property
    def tokens(self) -> int:
        return max(1, len(TOKEN_RE.findall(self.text)))


@dataclass(frozen=True)
class CodebaseContext:
    root: str
    query: str
    snapshot_digest: str
    chunks: tuple[ContextChunk, ...]
    relevant_paths: tuple[str, ...]
    unknowns: tuple[str, ...]
    token_estimate: int
    files_scanned: int
    files_read: int

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "query": self.query,
            "snapshot_digest": self.snapshot_digest,
            "relevant_paths": list(self.relevant_paths),
            "unknowns": list(self.unknowns),
            "token_estimate": self.token_estimate,
            "files_scanned": self.files_scanned,
            "files_read": self.files_read,
            "chunks": [
                {
                    "path": c.path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "score": c.score,
                    "reason": c.reason,
                    "text": c.text,
                }
                for c in self.chunks
            ],
        }


@dataclass
class CodebaseIndex:
    root: Path
    files: dict[str, FileRecord] = field(default_factory=dict)

    @classmethod
    def build(cls, root: str | Path, *, ignores: Iterable[str] = DEFAULT_IGNORES) -> "CodebaseIndex":
        root_path = Path(root).resolve()
        ignored = set(ignores)
        records: dict[str, FileRecord] = {}
        for current, dirs, names in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in ignored and not d.startswith(".")]
            for name in names:
                path = Path(current) / name
                rel = path.relative_to(root_path).as_posix()
                if path.suffix.lower() not in TEXT_EXTENSIONS or path.is_symlink():
                    continue
                try:
                    data = path.read_bytes()
                    text = data.decode("utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                symbols, imports = _extract_structure(rel, text)
                records[rel] = FileRecord(
                    rel,
                    len(data),
                    hashlib.sha256(data).hexdigest(),
                    text.count("\n") + (1 if text else 0),
                    tuple(symbols),
                    tuple(imports),
                )
        return cls(root_path, records)

    def digest(self) -> str:
        payload = "\n".join(
            f"{r.path}|{r.size}|{r.sha256}|{','.join(s.name for s in r.symbols)}|{','.join(r.imports)}"
            for r in sorted(self.files.values(), key=lambda x: x.path)
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_structure(path: str, text: str) -> tuple[list[Symbol], list[str]]:
    symbols: list[Symbol] = []
    imports: list[str] = []
    if path.endswith((".py", ".pyi")):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append(Symbol(node.name, type(node).__name__, path, node.lineno))
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
    else:
        for i, line in enumerate(text.splitlines(), 1):
            match = re.search(r"\b(?:class|interface|struct|enum|function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
            if match:
                symbols.append(Symbol(match.group(1), "declaration", path, i))
            if re.search(r"^\s*(?:import|using|require|from)\b", line):
                imports.append(line.strip())
    return symbols, imports


def _query_terms(query: str) -> tuple[str, ...]:
    terms = {t.lower() for t in TOKEN_RE.findall(query) if len(t) > 1}
    return tuple(sorted(terms, key=lambda x: (-len(x), x)))


def _rank_files(index: CodebaseIndex, query: str) -> list[tuple[float, FileRecord, str]]:
    terms = _query_terms(query)
    ranked: list[tuple[float, FileRecord, str]] = []
    for record in index.files.values():
        path_lower = record.path.lower()
        symbol_names = " ".join(s.name.lower() for s in record.symbols)
        import_names = " ".join(record.imports).lower()
        score = 0.0
        reasons: list[str] = []
        for term in terms:
            if term in path_lower:
                score += 6.0
                reasons.append(f"path:{term}")
            if term in symbol_names:
                score += 8.0
                reasons.append(f"symbol:{term}")
            if term in import_names:
                score += 2.0
                reasons.append(f"import:{term}")
        if record.path.lower() in {"readme.md", "pyproject.toml", "package.json", "go.mod", "cargo.toml"}:
            score += 0.5
        if score:
            ranked.append((score, record, ",".join(reasons[:5])))
    return sorted(ranked, key=lambda item: (-item[0], item[1].path))


def retrieve(
    index: CodebaseIndex,
    query: str,
    *,
    token_budget: int = 4000,
    max_files: int = 12,
    context_lines: int = 20,
) -> CodebaseContext:
    """Retrieve the smallest useful evidence set and expose unresolved areas."""
    if token_budget < 1 or max_files < 1 or context_lines < 1:
        raise ValueError("token_budget, max_files and context_lines must be positive")
    ranked = _rank_files(index, query)
    chunks: list[ContextChunk] = []
    unknowns: list[str] = []
    files_read = 0
    terms = _query_terms(query)

    if not ranked:
        unknowns.append("No indexed file path, symbol, or import matched the query")

    for score, record, reason in ranked[:max_files]:
        path = index.root / record.path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            unknowns.append(f"Unable to read {record.path}")
            continue
        files_read += 1
        lines = text.splitlines()
        hit_lines = [i for i, line in enumerate(lines) if any(term in line.lower() for term in terms)]
        if not hit_lines and record.symbols:
            hit_lines = [max(0, s.line - 1) for s in record.symbols[:2]]
        if not hit_lines:
            hit_lines = [0]
        selected: set[int] = set()
        for hit in hit_lines[:4]:
            start = max(0, hit - context_lines // 2)
            end = min(len(lines), start + context_lines)
            selected.update(range(start, end))
        if not selected:
            unknowns.append(f"No readable evidence window found in {record.path}")
            continue
        start = min(selected)
        end = max(selected) + 1
        snippet = "\n".join(lines[start:end])
        chunk = ContextChunk(record.path, start + 1, end, snippet, score, reason or "ranked-file")
        if sum(c.tokens for c in chunks) + chunk.tokens > token_budget:
            continue
        chunks.append(chunk)
        if sum(c.tokens for c in chunks) >= token_budget:
            break

    relevant = tuple(c.path for c in chunks)
    if ranked and not chunks:
        unknowns.append("Relevant files were identified but the token budget was too small for an evidence window")
    covered = {c.path for c in chunks}
    omitted = [r.path for _, r, _ in ranked[:max_files] if r.path not in covered]
    if omitted:
        unknowns.append("Additional relevant files omitted from context budget: " + ", ".join(omitted))

    return CodebaseContext(
        root=str(index.root),
        query=query,
        snapshot_digest=index.digest(),
        chunks=tuple(chunks),
        relevant_paths=relevant,
        unknowns=tuple(unknowns),
        token_estimate=sum(c.tokens for c in chunks),
        files_scanned=len(index.files),
        files_read=files_read,
    )


def retrieve_from_path(root: str | Path, query: str, **kwargs: object) -> CodebaseContext:
    """Build a deterministic index and retrieve evidence in one call."""
    return retrieve(CodebaseIndex.build(root), query, **kwargs)
