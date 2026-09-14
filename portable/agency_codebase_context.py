"""Deterministic, evidence-first and graph-aware codebase retrieval.

Retrieval ranks a small seed set, then expands the indexed structural graph to
bring in callees, callers, interfaces/implementations, tests and configuration.
Every expansion is typed and confidence-scored; budget omissions and unresolved
paths remain explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ast
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable, Sequence

DEFAULT_IGNORES = frozenset({".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "coverage"})
TEXT_EXTENSIONS = frozenset({".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs", ".cpp", ".cc", ".h", ".hpp", ".c", ".sql", ".sh", ".ps1", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".txt", ".proto"})
CONFIG_NAMES = frozenset({"pyproject.toml", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "go.mod", "cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "appsettings.json", "appsettings.development.json", "web.config", "dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile", ".env.example"})
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")
DECL_RE = re.compile(r"\b(class|interface|struct|enum|function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(")
BASE_RE = re.compile(r"\b(?:extends|implements)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.I)
TEST_RE = re.compile(r"(^|[._/-])(test|tests|spec|specs)([._/-]|$)", re.I)


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
    calls: tuple[str, ...] = ()
    bases: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphEdge:
    source_path: str
    target_path: str
    kind: str
    confidence: float
    reason: str
    source_symbol: str = ""
    target_symbol: str = ""


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
class GraphTrace:
    seed_paths: tuple[str, ...]
    expanded_paths: tuple[str, ...]
    edges: tuple[GraphEdge, ...]
    stopped: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "seed_paths": list(self.seed_paths),
            "expanded_paths": list(self.expanded_paths),
            "stopped": list(self.stopped),
            "edges": [e.__dict__.copy() for e in self.edges],
        }


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
    graph_trace: GraphTrace = field(default_factory=lambda: GraphTrace((), (), (), ()))

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root, "query": self.query, "snapshot_digest": self.snapshot_digest,
            "relevant_paths": list(self.relevant_paths), "unknowns": list(self.unknowns),
            "token_estimate": self.token_estimate, "files_scanned": self.files_scanned,
            "files_read": self.files_read, "graph_trace": self.graph_trace.as_dict(),
            "chunks": [c.__dict__ | {"tokens": c.tokens} for c in self.chunks],
        }


@dataclass
class CodebaseIndex:
    root: Path
    files: dict[str, FileRecord] = field(default_factory=dict)
    edges: tuple[GraphEdge, ...] = ()

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
                if path.is_symlink() or path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                try:
                    data = path.read_bytes(); text = data.decode("utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                symbols, imports, calls, bases = _extract_structure(rel, text)
                records[rel] = FileRecord(rel, len(data), hashlib.sha256(data).hexdigest(), text.count("\n") + bool(text), tuple(symbols), tuple(imports), tuple(calls), tuple(bases))
        index = cls(root_path, records)
        index.edges = tuple(_build_edges(index))
        return index

    def digest(self) -> str:
        payload = "\n".join(f"{r.path}|{r.size}|{r.sha256}|{','.join(s.name for s in r.symbols)}|{','.join(r.imports)}|{','.join(r.calls)}|{','.join(r.bases)}" for r in sorted(self.files.values(), key=lambda x: x.path))
        return hashlib.sha256(payload.encode()).hexdigest()

    def neighbors(self, path: str, *, kinds: Sequence[str] = ()) -> tuple[GraphEdge, ...]:
        allowed = set(kinds)
        return tuple(e for e in self.edges if (e.source_path == path or e.target_path == path) and (not allowed or e.kind in allowed))


def _ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        left = _ast_name(node.value); return f"{left}.{node.attr}" if left else node.attr
    return ""


def _extract_structure(path: str, text: str) -> tuple[list[Symbol], list[str], list[str], list[str]]:
    symbols: list[Symbol] = []; imports: list[str] = []; calls: list[str] = []; bases: list[str] = []
    if path.endswith((".py", ".pyi")):
        try: tree = ast.parse(text)
        except SyntaxError: tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    symbols.append(Symbol(node.name, kind, path, node.lineno))
                    if isinstance(node, ast.ClassDef): bases.extend(_ast_name(x) for x in node.bases if _ast_name(x))
                elif isinstance(node, ast.Import): imports.extend(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
                elif isinstance(node, ast.Call):
                    name = _ast_name(node.func)
                    if name: calls.append(name)
    else:
        for line_no, line in enumerate(text.splitlines(), 1):
            match = DECL_RE.search(line)
            if match:
                kind = "interface" if match.group(1).lower() == "interface" else "class" if match.group(1).lower() == "class" else "function"
                symbols.append(Symbol(match.group(2), kind, path, line_no))
            if re.search(r"^\s*(?:import|using|require|from)\b", line): imports.append(line.strip())
            calls.extend(m.group(1) for m in CALL_RE.finditer(line))
            bases.extend(m.group(1) for m in BASE_RE.finditer(line))
    return symbols, imports, calls, bases


def _module_variants(value: str) -> set[str]:
    value = re.sub(r"^(?:import|using|from|require)\s+", "", value.strip().strip("\"'"), flags=re.I)
    value = value.split()[0] if value else value
    value = value.replace("\\", "/").replace(".", "/")
    return {value.lstrip("/")}


def _resolve_import(index: CodebaseIndex, imported: str) -> list[str]:
    variants = _module_variants(imported); out = []
    for path in index.files:
        stem = Path(path).with_suffix("").as_posix()
        if any(stem == v or stem.endswith("/" + v) or Path(path).stem == v.split("/")[-1] for v in variants): out.append(path)
    return sorted(set(out))


def _build_edges(index: CodebaseIndex) -> list[GraphEdge]:
    edges: list[GraphEdge] = []; symbol_paths: dict[str, set[str]] = {}
    for record in index.files.values():
        for symbol in record.symbols: symbol_paths.setdefault(symbol.name.lower(), set()).add(record.path)
    config_text: dict[str, str] = {}
    for record in index.files.values():
        for imported in record.imports:
            for target in _resolve_import(index, imported)[:4]: edges.append(GraphEdge(record.path, target, "imports", .90, f"resolved-import:{imported}"))
        for base in record.bases:
            name = base.split(".")[-1].lower()
            for target in sorted(symbol_paths.get(name, ())):
                edges.append(GraphEdge(record.path, target, "implements", .85, f"base-type:{base}", target_symbol=name))
        for call in record.calls:
            name = call.split(".")[-1].lower(); candidates = sorted(symbol_paths.get(name, ()))
            if not candidates: continue
            confidence = .95 if record.path in candidates else .75 if len(candidates) == 1 else .50
            target = record.path if record.path in candidates else candidates[0]
            edges.append(GraphEdge(record.path, target, "calls", confidence, f"symbol-resolution:{call}", target_symbol=name))
        if Path(record.path).name.lower() in CONFIG_NAMES or ".github/" in record.path.lower():
            try: config_text[record.path] = (index.root / record.path).read_text(encoding="utf-8", errors="ignore").lower()
            except OSError: pass
    tests = [p for p in index.files if TEST_RE.search(p)]
    for test in tests:
        record = index.files[test]; refs = {x.split(".")[-1].lower() for x in record.calls + record.imports}
        for target, target_record in index.files.items():
            if target == test or TEST_RE.search(target): continue
            if Path(target).stem.lower() in refs or any(s.name.lower() in refs for s in target_record.symbols):
                edges.append(GraphEdge(test, target, "tests", .70, "test-name-or-symbol-reference"))
    for config, text in config_text.items():
        for target in index.files:
            if target != config and Path(target).stem.lower() in text:
                edges.append(GraphEdge(config, target, "configures", .65, "configuration-name-reference"))
    unique = {(e.source_path, e.target_path, e.kind, e.source_symbol, e.target_symbol): e for e in edges}
    return list(unique.values())


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(sorted({x.lower() for x in TOKEN_RE.findall(query) if len(x) > 1}, key=lambda x: (-len(x), x)))


def _rank_files(index: CodebaseIndex, query: str) -> list[tuple[float, FileRecord, str]]:
    terms = _query_terms(query); ranked = []
    for record in index.files.values():
        path = record.path.lower(); symbols = " ".join(s.name.lower() for s in record.symbols); imports = " ".join(record.imports).lower(); score = 0.; reasons = []
        for term in terms:
            if term in path: score += 6.; reasons.append(f"path:{term}")
            if term in symbols: score += 8.; reasons.append(f"symbol:{term}")
            if term in imports: score += 2.; reasons.append(f"import:{term}")
        if Path(record.path).name.lower() in CONFIG_NAMES or TEST_RE.search(record.path): score += .5
        if score: ranked.append((score, record, ",".join(reasons[:5])))
    return sorted(ranked, key=lambda x: (-x[0], x[1].path))


def _expand_graph(index: CodebaseIndex, seeds: Sequence[str], hops: int) -> tuple[list[tuple[str, float, str]], GraphTrace]:
    limit = max(0, min(2, hops)); seen = set(seeds); frontier = list(seeds); ranked = []; selected = []; stopped = []
    for depth in range(1, limit + 1):
        nxt = []
        for path in frontier:
            for edge in index.neighbors(path):
                other = edge.target_path if edge.source_path == path else edge.source_path
                if other in seen: continue
                if edge.kind == "calls": relation, weight = ("callee", 5.) if edge.source_path == path else ("caller", 4.5)
                elif edge.kind == "implements": relation, weight = "interface-or-implementation", 4.
                elif edge.kind == "tests": relation, weight = "test", 3.5
                elif edge.kind == "configures": relation, weight = "configuration", 3.
                else: relation, weight = "dependency", 3.
                ranked.append((other, weight * edge.confidence / depth, f"graph:{relation}:{edge.reason}")); selected.append(edge); seen.add(other); nxt.append(other)
        frontier = nxt
        if depth == limit and frontier: stopped.append("hop_budget_exhausted")
    if not selected and seeds: stopped.append("no_graph_successors")
    best: dict[str, tuple[float, str]] = {}
    for path, score, reason in ranked:
        if path not in best or score > best[path][0]: best[path] = (score, reason)
    expanded = sorted(((p, s, r) for p, (s, r) in best.items()), key=lambda x: (-x[1], x[0]))
    return expanded, GraphTrace(tuple(seeds), tuple(p for p, _, _ in expanded), tuple(selected), tuple(stopped))


def retrieve(index: CodebaseIndex, query: str, *, token_budget: int = 4000, max_files: int = 12, context_lines: int = 20, graph_hops: int = 2) -> CodebaseContext:
    """Retrieve minimal seed evidence plus a bounded structural neighborhood."""
    if token_budget < 1 or max_files < 1 or context_lines < 1: raise ValueError("token_budget, max_files and context_lines must be positive")
    ranked = _rank_files(index, query); unknowns = []
    if not ranked:
        unknowns.append("No indexed file path, symbol, or import matched the query")
        trace = GraphTrace((), (), (), ("no_seed_match",))
        return CodebaseContext(str(index.root), query, index.digest(), (), (), tuple(unknowns), 0, len(index.files), 0, trace)
    seeds = [r.path for _, r, _ in ranked[:min(3, max_files)]]
    graph_ranked, trace = _expand_graph(index, seeds, graph_hops)
    candidates: dict[str, tuple[float, str]] = {r.path: (s, why or "ranked-file") for s, r, why in ranked[:max_files]}
    for path, score, reason in graph_ranked:
        if path not in candidates or score > candidates[path][0]: candidates[path] = (score, reason)
    ordered = sorted(candidates.items(), key=lambda x: (-x[1][0], x[0]))[:max_files]
    chunks: list[ContextChunk] = []; files_read = 0; terms = _query_terms(query); used = 0
    for path, (score, reason) in ordered:
        try: text = (index.root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError): unknowns.append(f"Unable to read {path}"); continue
        files_read += 1; lines = text.splitlines(); hits = [i for i, line in enumerate(lines) if any(t in line.lower() for t in terms)]
        if not hits: hits = [s.line - 1 for s in index.files[path].symbols[:2]] or [0]
        selected: set[int] = set()
        for hit in hits[:4]:
            start = max(0, hit - context_lines // 2); selected.update(range(start, min(len(lines), start + context_lines)))
        if not selected: unknowns.append(f"No readable evidence window found in {path}"); continue
        start, end = min(selected), max(selected) + 1; chunk = ContextChunk(path, start + 1, end, "\n".join(lines[start:end]), score, reason)
        if used + chunk.tokens > token_budget: continue
        chunks.append(chunk); used += chunk.tokens
        if used >= token_budget: break
    omitted = [p for p, _ in ordered if p not in {c.path for c in chunks}]
    if omitted: unknowns.append("Relevant files omitted from context budget: " + ", ".join(omitted))
    unknowns.extend(f"Graph retrieval stopped: {x}" for x in trace.stopped)
    return CodebaseContext(str(index.root), query, index.digest(), tuple(chunks), tuple(c.path for c in chunks), tuple(dict.fromkeys(unknowns)), used, len(index.files), files_read, trace)


def retrieve_from_path(root: str | Path, query: str, **kwargs: object) -> CodebaseContext:
    return retrieve(CodebaseIndex.build(root), query, **kwargs)
