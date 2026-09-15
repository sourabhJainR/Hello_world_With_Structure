"""Dependency-free deterministic repository intelligence for AER.

This module adapts useful repository-mapping ideas: one stable snapshot, ranked
structural retrieval, shallow graph questions, explicit budgets and honest
uncertainty. It contains no ripwire code and has no runtime dependency on it.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

DEFAULT_IGNORES = frozenset({".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build", "out", "target", "coverage", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".idea", ".vscode", "worktrees"})
TEXT_EXTENSIONS = frozenset({".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".swift", ".kt", ".kts", ".rb", ".php", ".lua", ".ex", ".exs", ".sh", ".ps1", ".sql", ".md", ".markdown", ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf", ".proto"})
GENERATED_NAMES = frozenset({"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"})
TEST_RE = re.compile(r"(^|[._/\\-])(test|tests|spec|specs)([._/\\-]|$)", re.I)
DECL_RE = re.compile(r"\b(class|interface|struct|enum|function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(")
IMPORT_RE = re.compile(r"^\s*(?:import|using|from|require)\b(.+)$", re.I)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")

@dataclass(frozen=True)
class Symbol:
    name: str; kind: str; path: str; start_line: int; end_line: int; signature: str = ""

@dataclass(frozen=True)
class FileRecord:
    path: str; size: int; sha256: str; lines: int
    symbols: tuple[Symbol, ...] = (); imports: tuple[str, ...] = (); calls: tuple[str, ...] = ()
    generated: bool = False; test: bool = False; parse_error: str | None = None

@dataclass(frozen=True)
class Edge:
    source: str; target: str; kind: str; confidence: float; reason: str; symbol: str = ""

@dataclass(frozen=True)
class Evidence:
    path: str; start_line: int; end_line: int; text: str; score: float; reason: str

@dataclass(frozen=True)
class RepoAnswer:
    schema_version: int; query: str; snapshot: str; mode: str
    evidence: tuple[Evidence, ...]; files: tuple[str, ...]; edges: tuple[Edge, ...]
    unknowns: tuple[str, ...]; metrics: dict[str, int | float]; token_estimate: int
    def as_dict(self) -> dict: return asdict(self)

@dataclass
class RepositoryMap:
    root: Path
    files: dict[str, FileRecord] = field(default_factory=dict)
    edges: tuple[Edge, ...] = ()
    skipped: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @classmethod
    def build(cls, root: str | Path, *, ignores: Iterable[str] = DEFAULT_IGNORES, max_file_size: int = 4 * 1024 * 1024) -> "RepositoryMap":
        root = Path(root).resolve(); ignored = set(ignores); records = {}; skipped = defaultdict(int)
        for current, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in ignored and not d.startswith("."))
            for name in sorted(names):
                path = Path(current) / name; rel = path.relative_to(root).as_posix()
                if path.is_symlink(): skipped["symlink"] += 1; continue
                if path.suffix.lower() not in TEXT_EXTENSIONS: skipped["unindexed_extension"] += 1; continue
                try: data = path.read_bytes()
                except OSError: skipped["unreadable"] += 1; continue
                if len(data) > max_file_size: skipped["oversize"] += 1; continue
                if b"\0" in data[:4096]: skipped["binary"] += 1; continue
                try: text = data.decode("utf-8")
                except UnicodeDecodeError: skipped["invalid_utf8"] += 1; continue
                symbols, imports, calls, error = _extract(rel, text)
                records[rel] = FileRecord(rel, len(data), hashlib.sha256(data).hexdigest(), len(text.splitlines()), tuple(symbols), tuple(imports), tuple(calls), Path(rel).name.lower() in GENERATED_NAMES, bool(TEST_RE.search(rel)), error)
        result = cls(root, records, (), skipped); result.edges = tuple(_build_edges(result)); return result

    def digest(self) -> str:
        rows = []
        for r in sorted(self.files.values(), key=lambda x: x.path):
            rows.append({"path": r.path, "sha256": r.sha256, "symbols": [(s.name, s.kind, s.start_line, s.end_line) for s in r.symbols], "imports": r.imports, "calls": r.calls})
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def symbol_matches(self, query: str) -> list[Symbol]:
        terms = _terms(query); rows = []
        for r in self.files.values():
            for s in r.symbols:
                score = sum(8.0 if t == s.name.lower() else 4.0 for t in terms if t in s.name.lower())
                if score: rows.append((score, s))
        return [s for _, s in sorted(rows, key=lambda x: (-x[0], x[1].path, x[1].start_line))]

    def callers(self, symbol: str) -> tuple[Edge, ...]:
        key = symbol.lower().split(".")[-1]
        return tuple(e for e in self.edges if e.kind == "calls" and e.symbol.lower().split(".")[-1] == key)

    def callees(self, symbol: str) -> tuple[Edge, ...]:
        paths = {s.path for s in self.symbol_matches(symbol) if s.name.lower() == symbol.lower().split(".")[-1]}
        return tuple(e for e in self.edges if e.kind == "calls" and e.source in paths)

    def impact(self, symbol: str, depth: int = 2) -> tuple[Edge, ...]:
        seeds = {e.source for e in self.callers(symbol)} | {e.target for e in self.callers(symbol)}
        seen = set(seeds); queue = deque((p, 0) for p in sorted(seeds)); found = []
        while queue:
            path, level = queue.popleft()
            if level > max(0, min(2, depth)): continue
            for e in self.edges:
                if e.source != path and e.target != path: continue
                found.append(e); other = e.target if e.source == path else e.source
                if other not in seen and level < depth: seen.add(other); queue.append((other, level + 1))
        return _unique(found)

    def affected_tests(self, changed: Iterable[str]) -> tuple[str, ...]:
        changed_set = {Path(p).as_posix() for p in changed}; reverse = defaultdict(set)
        for e in self.edges: reverse[e.target].add(e.source)
        found = {p for p in changed_set if p in self.files and self.files[p].test}; queue = deque(changed_set); seen = set(changed_set)
        while queue:
            current = queue.popleft()
            for parent in reverse.get(current, ()):
                if parent in seen: continue
                seen.add(parent); queue.append(parent)
                if parent in self.files and self.files[parent].test: found.add(parent)
        for test in self.files.values():
            if not test.test: continue
            text = _read(self.root / test.path) or ""
            if any(Path(p).stem.lower() in text.lower() for p in changed_set): found.add(test.path)
        return tuple(sorted(found))

    def changed_files(self, base: str = "HEAD") -> tuple[str, ...]:
        try: proc = subprocess.run(["git", "diff", "--name-only", base, "--"], cwd=self.root, text=True, capture_output=True, check=False, timeout=8)
        except (OSError, subprocess.TimeoutExpired): return ()
        return tuple(sorted(x.strip().replace("\\", "/") for x in proc.stdout.splitlines() if x.strip())) if proc.returncode == 0 else ()

    def answer(self, query: str, *, mode: str = "search", token_budget: int = 4000, max_files: int = 12, context_lines: int = 24, graph_depth: int = 1, base: str = "HEAD") -> RepoAnswer:
        if min(token_budget, max_files, context_lines) < 1: raise ValueError("budgets and limits must be positive")
        unknowns = []; edges: tuple[Edge, ...] = ()
        if mode == "situ":
            changed = self.changed_files(base); query = query or "changed files"
            ranked = [(12.0, self.files[p], "git:changed") for p in changed if p in self.files]
            tests = self.affected_tests(changed); ranked += [(8.0, self.files[p], "test:candidate") for p in tests if p in self.files and p not in changed]
            if not changed: unknowns.append("No git diff was available; changed-file state is unknown")
        else:
            ranked = _rank(self, query); matches = self.symbol_matches(query)
            ranked = _dedupe([(20.0, self.files[s.path], f"symbol:{s.name}") for s in matches[:max_files]] + ranked)
            seeds = [r.path for _, r, _ in ranked[:min(3, max_files)]]; edges = self._neighborhood(seeds, graph_depth)
            if mode == "callers": edges = self.callers(query)
            elif mode == "callees": edges = self.callees(query)
            elif mode == "impact": edges = self.impact(query, graph_depth)
            elif mode == "tests":
                tests = self.affected_tests([s.path for s in matches]); ranked = [(14.0, self.files[p], "test:candidate") for p in tests if p in self.files]
                if not ranked: unknowns.append("No affected-test candidate found; this does not prove there are no tests")
            elif mode == "pack-task": ranked = _dedupe(ranked + [(6.0, self.files[e.target], f"graph:{e.kind}") for e in edges if e.target in self.files])
        if not ranked and mode != "situ": unknowns.append("No indexed path or symbol matched; no absence claim is made")
        evidence = []; used = 0; selected = []
        for score, record, reason in ranked[:max_files]:
            text = _read(self.root / record.path)
            if text is None: unknowns.append(f"Unable to read selected file: {record.path}"); continue
            lines = text.splitlines(); anchors = _anchors(record, query, lines)
            for anchor in anchors[:4]:
                start = max(0, anchor - context_lines // 2); end = min(len(lines), start + context_lines); chunk = "\n".join(lines[start:end]); cost = _tokens(chunk)
                if used + cost > token_budget: unknowns.append(f"Context budget omitted evidence from {record.path}"); break
                evidence.append(Evidence(record.path, start + 1, end, chunk, score, reason)); used += cost; selected.append(record.path)
                if used >= token_budget: break
            if used >= token_budget: break
        if used >= token_budget or len(selected) < min(len(ranked), max_files): unknowns.append("Answer is budget-bounded; selected files are not a completeness proof")
        parse_errors = sum(1 for r in self.files.values() if r.parse_error)
        if parse_errors: unknowns.append(f"{parse_errors} files had parser fallback/errors; relationships may be incomplete")
        if self.skipped: unknowns.append("Skipped inventory: " + ", ".join(f"{k}={v}" for k, v in sorted(self.skipped.items())))
        metrics = {"files_indexed": len(self.files), "edges": len(self.edges), "files_skipped": sum(self.skipped.values()), "ambiguous_edges": sum(1 for e in self.edges if e.confidence < .75), "parse_errors": parse_errors, "evidence_items": len(evidence)}
        return RepoAnswer(1, query, self.digest(), mode, tuple(evidence), tuple(dict.fromkeys(selected)), tuple(edges), tuple(dict.fromkeys(unknowns)), metrics, used)

    def _neighborhood(self, seeds: Iterable[str], depth: int) -> tuple[Edge, ...]:
        frontier = set(seeds); seen = set(frontier); found = []
        for _ in range(max(0, min(2, depth))):
            nxt = set()
            for e in self.edges:
                if e.source not in frontier and e.target not in frontier: continue
                found.append(e); other = e.target if e.source in frontier else e.source
                if other not in seen: seen.add(other); nxt.add(other)
            frontier = nxt
            if not frontier: break
        return _unique(found)


def _read(path: Path) -> str | None:
    try: return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError): return None

def _extract(path: str, text: str):
    symbols = []; imports = []; calls = []; error = None
    if path.endswith((".py", ".pyi")):
        try: tree = ast.parse(text)
        except SyntaxError as exc: tree = None; error = f"python syntax error at line {exc.lineno or '?'}"
        if tree:
            lines = text.splitlines()
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append(Symbol(n.name, "class" if isinstance(n, ast.ClassDef) else "function", path, n.lineno, getattr(n, "end_lineno", n.lineno), lines[n.lineno - 1].strip()))
                elif isinstance(n, (ast.Import, ast.ImportFrom)): imports.append(ast.unparse(n) if hasattr(ast, "unparse") else "import")
                elif isinstance(n, ast.Call):
                    name = _ast_name(n.func)
                    if name: calls.append(name)
    else:
        for no, line in enumerate(text.splitlines(), 1):
            m = DECL_RE.search(line)
            if m: symbols.append(Symbol(m.group(2), m.group(1).lower(), path, no, no, line.strip()))
            m = IMPORT_RE.search(line)
            if m: imports.append(m.group(1).strip())
            calls.extend(m.group(1) for m in CALL_RE.finditer(line))
    return symbols, imports, calls, error

def _ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        left = _ast_name(node.value); return f"{left}.{node.attr}" if left else node.attr
    return ""

def _build_edges(index: RepositoryMap) -> list[Edge]:
    result = []; symbol_paths = defaultdict(set)
    for r in index.files.values():
        for s in r.symbols: symbol_paths[s.name.lower()].add(r.path)
    for r in index.files.values():
        for imported in r.imports:
            for target in _resolve_import(index, imported)[:4]: result.append(Edge(r.path, target, "imports", .90, f"import:{imported}"))
        for call in r.calls:
            name = call.split(".")[-1].lower(); candidates = sorted(symbol_paths.get(name, ()))
            if not candidates: continue
            if r.path in candidates: result.append(Edge(r.path, r.path, "calls", .95, f"symbol:{call}", call))
            elif len(candidates) == 1: result.append(Edge(r.path, candidates[0], "calls", .78, f"symbol:{call}", call))
            else:
                for target in candidates[:4]: result.append(Edge(r.path, target, "calls", .45, f"ambiguous-symbol:{call}", call))
    for test in index.files.values():
        if not test.test: continue
        text = (_read(index.root / test.path) or "").lower()
        for target in index.files.values():
            if target.test or target.path == test.path: continue
            if Path(target.path).stem.lower() in text: result.append(Edge(test.path, target.path, "tests", .65, "test-file-reference"))
    return list({(e.source, e.target, e.kind, e.symbol): e for e in result}.values())

def _resolve_import(index: RepositoryMap, value: str) -> list[str]:
    value = re.sub(r"^(?:import|using|from|require)\s+", "", value.strip().strip("\"'"), flags=re.I).split()[0] if value.strip() else ""
    value = value.replace("\\", "/").replace(".", "/").lstrip("/")
    return sorted({p for p in index.files if Path(p).with_suffix("").as_posix() == value or Path(p).stem == value.split("/")[-1]})

def _terms(query: str) -> tuple[str, ...]: return tuple(sorted({x.lower() for x in TOKEN_RE.findall(query) if len(x) > 1}, key=lambda x: (-len(x), x)))
def _rank(index: RepositoryMap, query: str):
    terms = _terms(query); rows = []
    for r in index.files.values():
        path = r.path.lower(); symbols = " ".join(s.name.lower() for s in r.symbols); imports = " ".join(r.imports).lower(); score = 0.; reasons = []
        for t in terms:
            if t in path: score += 7; reasons.append(f"path:{t}")
            if t in symbols: score += 9; reasons.append(f"symbol:{t}")
            if t in imports: score += 2; reasons.append(f"import:{t}")
        if r.test: score += .25
        if r.generated: score -= 3
        if score: rows.append((score, r, ",".join(reasons[:5])))
    return sorted(rows, key=lambda x: (-x[0], x[1].path))
def _dedupe(rows):
    best = {}
    for row in rows:
        if row[1].path not in best or row[0] > best[row[1].path][0]: best[row[1].path] = row
    return sorted(best.values(), key=lambda x: (-x[0], x[1].path))
def _unique(edges): return tuple({(e.source, e.target, e.kind, e.symbol): e for e in edges}.values())
def _anchors(record, query, lines):
    terms = _terms(query); hits = [i for i, line in enumerate(lines) if any(t in line.lower() for t in terms)]
    return hits or [s.start_line - 1 for s in record.symbols[:3]] or [0]
def _tokens(text): return max(1, len(TOKEN_RE.findall(text)) + len(text) // 24)

def render_compact(answer: RepoAnswer) -> str:
    out = [f"AER-REPO-MAP v{answer.schema_version} mode={answer.mode} est_tokens={answer.token_estimate} snapshot={answer.snapshot[:12]}", f"files={len(answer.files)} edges={len(answer.edges)} unknowns={len(answer.unknowns)}"]
    for e in answer.evidence:
        out.append(f"FILE {e.path}:{e.start_line}-{e.end_line} score={e.score:.2f} reason={e.reason}"); out.extend("  " + x for x in e.text.splitlines())
    for e in answer.edges: out.append(f"EDGE {e.kind} {e.source} -> {e.target} confidence={e.confidence:.2f} symbol={e.symbol} reason={e.reason}")
    for u in answer.unknowns: out.append(f"UNKNOWN {u}")
    return "\n".join(out) + "\n"

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AER deterministic repository intelligence map"); p.add_argument("root", nargs="?", default="."); p.add_argument("--for", dest="query", default=""); p.add_argument("--mode", choices=("search", "callers", "callees", "impact", "tests", "situ", "pack-task"), default="search"); p.add_argument("--symbol", default=""); p.add_argument("--base", default="HEAD"); p.add_argument("--token-budget", type=int, default=4000); p.add_argument("--max-files", type=int, default=12); p.add_argument("--graph-depth", type=int, default=1); p.add_argument("--json", action="store_true"); a = p.parse_args(argv)
    answer = RepositoryMap.build(a.root).answer(a.symbol or a.query, mode=a.mode, token_budget=a.token_budget, max_files=a.max_files, graph_depth=a.graph_depth, base=a.base)
    print(json.dumps(answer.as_dict(), indent=2, sort_keys=True) if a.json else render_compact(answer), end=""); return 0

if __name__ == "__main__": raise SystemExit(main())
