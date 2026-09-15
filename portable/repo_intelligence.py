"""Deterministic, dependency-free repository intelligence for AER.

Inspired by the useful engineering ideas observed in ripwire: build one stable
repository model, answer task-shaped questions from the same graph, budget the
answer, and disclose uncertainty instead of hiding missing edges or omitted
context. No ripwire code is used here and no runtime dependency is introduced.
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

DEFAULT_IGNORES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    "out", "target", "coverage", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".idea", ".vscode", "worktrees",
})
TEXT_EXTENSIONS = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs",
    ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".swift", ".kt", ".kts", ".rb",
    ".php", ".lua", ".ex", ".exs", ".sh", ".ps1", ".sql", ".md", ".markdown",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf", ".proto",
})
GENERATED_NAMES = frozenset({"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"})
TEST_RE = re.compile(r"(^|[._/\\-])(test|tests|spec|specs)([._/\\-]|$)", re.I)
DECL_RE = re.compile(r"\b(class|interface|struct|enum|function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(")
IMPORT_RE = re.compile(r"^\s*(?:import|using|from|require)\b(.+)$", re.I)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")

@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    path: str
    start_line: int
    end_line: int
    signature: str = ""

@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str
    lines: int
    symbols: tuple[Symbol, ...] = ()
    imports: tuple[str, ...] = ()
    calls: tuple[str, ...] = ()
    generated: bool = False
    test: bool = False
    parse_error: str | None = None

@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str
    confidence: float
    reason: str

@dataclass(frozen=True)
class Evidence:
    path: str
    start_line: int
    end_line: int
    text: str
    score: float
    reason: str

@dataclass(frozen=True)
class RepoAnswer:
    schema_version: int
    query: str
    snapshot: str
    mode: str
    evidence: tuple[Evidence, ...]
    files: tuple[str, ...]
    edges: tuple[Edge, ...]
    unknowns: tuple[str, ...]
    metrics: dict[str, int | float]
    token_estimate: int

    def as_dict(self) -> dict:
        return asdict(self)

@dataclass
class RepositoryMap:
    root: Path
    files: dict[str, FileRecord] = field(default_factory=dict)
    edges: tuple[Edge, ...] = ()
    skipped: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @classmethod
    def build(
        cls, root: str | Path, *, ignores: Iterable[str] = DEFAULT_IGNORES,
        max_file_size: int = 4 * 1024 * 1024,
    ) -> "RepositoryMap":
        root_path = Path(root).resolve()
        ignored = set(ignores)
        records: dict[str, FileRecord] = {}
        skipped: dict[str, int] = defaultdict(int)
        for current, dirs, names in os.walk(root_path, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in ignored and not d.startswith("."))
            for name in sorted(names):
                path = Path(current) / name
                rel = path.relative_to(root_path).as_posix()
                if path.is_symlink():
                    skipped["symlink"] += 1
                    continue
                if path.suffix.lower() not in TEXT_EXTENSIONS:
                    skipped["unindexed_extension"] += 1
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    skipped["unreadable"] += 1
                    continue
                if len(data) > max_file_size:
                    skipped["oversize"] += 1
                    continue
                if b"\0" in data[:4096]:
                    skipped["binary"] += 1
                    continue
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    skipped["invalid_utf8"] += 1
                    continue
                symbols, imports, calls, parse_error = _extract(rel, text)
                records[rel] = FileRecord(
                    rel, len(data), hashlib.sha256(data).hexdigest(),
                    len(text.splitlines()), tuple(symbols), tuple(imports), tuple(calls),
                    Path(rel).name.lower() in GENERATED_NAMES, bool(TEST_RE.search(rel)), parse_error,
                )
        result = cls(root_path, records, (), skipped)
        result.edges = tuple(_build_edges(result))
        return result

    def digest(self) -> str:
        payload = []
        for record in sorted(self.files.values(), key=lambda r: r.path):
            payload.append({
                "path": record.path, "sha256": record.sha256,
                "symbols": [(s.name, s.kind, s.start_line, s.end_line) for s in record.symbols],
                "imports": record.imports, "calls": record.calls,
            })
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def symbol_matches(self, query: str) -> list[Symbol]:
        terms = _terms(query)
        matches = []
        for record in self.files.values():
            for symbol in record.symbols:
                name = symbol.name.lower()
                score = sum(8.0 if t == name else 4.0 for t in terms if t in name)
                if score:
                    matches.append((score, symbol))
        return [s for _, s in sorted(matches, key=lambda x: (-x[0], x[1].path, x[1].start_line))]

    def callers(self, symbol: str) -> tuple[Edge, ...]:
        key = symbol.lower().split(".")[-1]
        return tuple(e for e in self.edges if e.kind == "calls" and e.target.lower().endswith(key))

    def callees(self, symbol: str) -> tuple[Edge, ...]:
        key = symbol.lower()
        return tuple(e for e in self.edges if e.kind == "calls" and (e.source.lower() == key or Path(e.source).stem.lower() == key))

    def impact(self, symbol: str, depth: int = 2) -> tuple[Edge, ...]:
        seeds = {e.source for e in self.callers(symbol)} | {e.target for e in self.callers(symbol)}
        seen: set[str] = set()
        result: list[Edge] = []
        queue = deque((p, 0) for p in sorted(seeds))
        while queue:
            path, level = queue.popleft()
            if path in seen or level > max(0, depth):
                continue
            seen.add(path)
            for edge in self.edges:
                if edge.source != path and edge.target != path:
                    continue
                result.append(edge)
                other = edge.target if edge.source == path else edge.source
                if other not in seen and level < depth:
                    queue.append((other, level + 1))
        return _unique_edges(result)

    def affected_tests(self, changed: Iterable[str]) -> tuple[str, ...]:
        changed_set = {Path(p).as_posix() for p in changed}
        reverse = defaultdict(set)
        for edge in self.edges:
            reverse[edge.target].add(edge.source)
        found: set[str] = {p for p in changed_set if p in self.files and self.files[p].test}
        queue = deque(changed_set)
        seen = set(changed_set)
        while queue:
            current = queue.popleft()
            for parent in reverse.get(current, ()):
                if parent in seen:
                    continue
                seen.add(parent)
                queue.append(parent)
                if parent in self.files and self.files[parent].test:
                    found.add(parent)
        # Name/symbol fallback is deliberately conservative: it adds candidates,
        # never claims proof of execution coverage.
        for test in self.files.values():
            if not test.test:
                continue
            text = _read_text(self.root / test.path).lower()
            for changed_path in changed_set:
                stem = Path(changed_path).stem.lower()
                if stem and stem in text:
                    found.add(test.path)
        return tuple(sorted(found))

    def changed_files(self, base: str = "HEAD") -> tuple[str, ...]:
        try:
            proc = subprocess.run(
                ["git", "diff", "--name-only", base, "--"], cwd=self.root,
                text=True, capture_output=True, check=False, timeout=8,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ()
        if proc.returncode != 0:
            return ()
        return tuple(sorted(x.strip().replace("\\", "/") for x in proc.stdout.splitlines() if x.strip()))

    def answer(
        self, query: str, *, mode: str = "search", token_budget: int = 4000,
        max_files: int = 12, context_lines: int = 24, graph_depth: int = 1,
        base: str = "HEAD",
    ) -> RepoAnswer:
        if token_budget < 1 or max_files < 1 or context_lines < 1:
            raise ValueError("token_budget, max_files and context_lines must be positive")
        unknowns: list[str] = []
        edges: tuple[Edge, ...] = ()
        if mode == "situ":
            changed = self.changed_files(base)
            if not changed:
                unknowns.append("No git diff was available for the requested base; changed-file state is unknown")
            query = query or "changed files"
            ranked = [(12.0, self.files[p], "git:changed") for p in changed if p in self.files]
            tests = self.affected_tests(changed)
            ranked += [(8.0, self.files[p], "test:affected-candidate") for p in tests if p in self.files and p not in changed]
        else:
            ranked = _rank_files(self, query)
            symbols = self.symbol_matches(query)
            if symbols:
                ranked = [(20.0, self.files[s.path], f"symbol:{s.name}") for s in symbols[:max_files]] + ranked
            ranked = _dedupe_ranked(ranked)
            seeds = [r.path for _, r, _ in ranked[:min(3, max_files)]]
            edges = self._graph_neighborhood(seeds, graph_depth)
            if mode == "callers":
                edges = self.callers(query)
            elif mode == "callees":
                edges = self.callees(query)
            elif mode == "impact":
                edges = self.impact(query, graph_depth)
            elif mode == "tests":
                tests = self.affected_tests([s.path for s in self.symbol_matches(query)])
                ranked = [(14.0, self.files[p], "test:affected-candidate") for p in tests if p in self.files]
                if not ranked:
                    unknowns.append("No affected-test candidate was found; this does not prove there are no tests")
            elif mode == "pack-task":
                # Task packing is intentionally graph-first and remains bounded.
                ranked = _dedupe_ranked(ranked + [
                    (6.0, self.files[e.target], f"graph:{e.kind}")
                    for e in edges if e.target in self.files
                ])
        if not ranked and mode != "situ":
            unknowns.append("No indexed path or symbol matched the query; no absence claim is made")
        evidence: list[Evidence] = []
        used = 0
        selected_files: list[str] = []
        for score, record, reason in ranked[:max_files]:
            text = _read_text(self.root / record.path)
            if text is None:
                unknowns.append(f"Unable to read selected file: {record.path}")
                continue
            lines = text.splitlines()
            anchors = _anchors(record, query, lines)
            for anchor in anchors[:4]:
                start = max(0, anchor - context_lines // 2)
                end = min(len(lines), start + context_lines)
                chunk = "\n".join(lines[start:end])
                tokens = _estimate_tokens(chunk)
                if used + tokens > token_budget:
                    unknowns.append(f"Context budget omitted evidence from {record.path}")
                    break
                evidence.append(Evidence(record.path, start + 1, end, chunk, score, reason))
                used += tokens
                selected_files.append(record.path)
                if used >= token_budget:
                    break
            if used >= token_budget:
                break
        if len(selected_files) < min(len(ranked), max_files):
            unknowns.append("Answer is budget-bounded; selected files are not a completeness proof")
        parse_errors = sum(1 for r in self.files.values() if r.parse_error)
        if parse_errors:
            unknowns.append(f"{parse_errors} indexed files had parser fallback/errors; relationships may be incomplete")
        metrics = {
            "files_indexed": len(self.files),
            "edges": len(self.edges),
            "files_skipped": sum(self.skipped.values()),
            "unresolved_or_ambiguous_edges": sum(1 for e in self.edges if e.confidence < 0.75),
            "parse_errors": parse_errors,
            "evidence_items": len(evidence),
        }
        if self.skipped:
            unknowns.append("Skipped inventory: " + ", ".join(f"{k}={v}" for k, v in sorted(self.skipped.items())))
        return RepoAnswer(1, query, self.digest(), mode, tuple(evidence), tuple(dict.fromkeys(selected_files)), tuple(edges), tuple(dict.fromkeys(unknowns)), metrics, used)

    def _graph_neighborhood(self, seeds: Iterable[str], depth: int) -> tuple[Edge, ...]:
        frontier = set(seeds)
        seen = set(frontier)
        found: list[Edge] = []
        for _ in range(max(0, min(2, depth))):
            nxt: set[str] = set()
            for edge in self.edges:
                if edge.source not in frontier and edge.target not in frontier:
                    continue
                found.append(edge)
                other = edge.target if edge.source in frontier else edge.source
                if other not in seen:
                    seen.add(other); nxt.add(other)
            frontier = nxt
            if not frontier:
                break
        return _unique_edges(found)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _extract(path: str, text: str):
    symbols: list[Symbol] = []
    imports: list[str] = []
    calls: list[str] = []
    parse_error = None
    if path.endswith((".py", ".pyi")):
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    end = getattr(node, "end_lineno", node.lineno)
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    signature = text.splitlines()[node.lineno - 1].strip() if text.splitlines() else ""
                    symbols.append(Symbol(node.name, kind, path, node.lineno, end, signature))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node) if hasattr(ast, "unparse") else "import")
                elif isinstance(node, ast.Call):
                    name = _ast_name(node.func)
                    if name:
                        calls.append(name)
        except SyntaxError as exc:
            parse_error = f"python syntax error at line {exc.lineno or '?'}"
    else:
        lines = text.splitlines()
        for number, line in enumerate(lines, 1):
            match = DECL_RE.search(line)
            if match:
                symbols.append(Symbol(match.group(2), match.group(1).lower(), path, number, number, line.strip()))
            imp = IMPORT_RE.search(line)
            if imp:
                imports.append(imp.group(1).strip())
            calls.extend(m.group(1) for m in CALL_RE.finditer(line))
    return symbols, imports, calls, parse_error


def _ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _ast_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def _build_edges(index: RepositoryMap) -> list[Edge]:
    result: list[Edge] = []
    symbol_paths: dict[str, set[str]] = defaultdict(set)
    for record in index.files.values():
        for symbol in record.symbols:
            symbol_paths[symbol.name.lower()].add(record.path)
    for record in index.files.values():
        for imported in record.imports:
            candidates = _resolve_import(index, imported)
            for target in candidates[:4]:
                result.append(Edge(record.path, target, "imports", .90 if len(candidates) == 1 else .55, f"import:{imported}"))
        for call in record.calls:
            name = call.split(".")[-1].lower()
            candidates = sorted(symbol_paths.get(name, ()))
            if not candidates:
                continue
            if record.path in candidates:
                target, confidence = record.path, .95
            elif len(candidates) == 1:
                target, confidence = candidates[0], .78
            else:
                # Never invent a unique target when names collide. Keep the
                # candidate set visible with lower confidence for downstream gates.
                for candidate in candidates[:4]:
                    result.append(Edge(record.path, candidate, "calls", .45, f"ambiguous-symbol:{call}"))
                continue
            result.append(Edge(record.path, target, "calls", confidence, f"symbol:{call}"))
    # Test relationships are candidates, not proof of execution coverage.
    for test in index.files.values():
        if not test.test:
            continue
        names = {Path(p).stem.lower() for p in test.imports}
        names |= {c.split(".")[-1].lower() for c in test.calls}
        for target in index.files.values():
            if target.test or target.path == test.path:
                continue
            if Path(target.path).stem.lower() in names:
                result.append(Edge(test.path, target.path, "tests", .65, "test-import-or-call-reference"))
    return list({(e.source, e.target, e.kind, e.reason): e for e in result}.values())


def _resolve_import(index: RepositoryMap, value: str) -> list[str]:
    clean = value.strip().strip("\"'").replace("\\", "/")
    clean = re.sub(r"^(?:import|using|from|require)\s+", "", clean, flags=re.I).split()[0] if clean else ""
    clean = clean.replace(".", "/").lstrip("/")
    result = []
    for path in index.files:
        stem = Path(path).with_suffix("").as_posix()
        if stem == clean or stem.endswith("/" + clean) or Path(path).stem == clean.split("/")[-1]:
            result.append(path)
    return sorted(set(result))


def _terms(query: str) -> tuple[str, ...]:
    return tuple(sorted({x.lower() for x in TOKEN_RE.findall(query) if len(x) > 1}, key=lambda x: (-len(x), x)))


def _rank_files(index: RepositoryMap, query: str):
    terms = _terms(query)
    ranked = []
    for record in index.files.values():
        path = record.path.lower()
        symbols = " ".join(s.name.lower() for s in record.symbols)
        imports = " ".join(record.imports).lower()
        score = 0.0
        reasons = []
        for term in terms:
            if term in path:
                score += 7; reasons.append(f"path:{term}")
            if term in symbols:
                score += 9; reasons.append(f"symbol:{term}")
            if term in imports:
                score += 2; reasons.append(f"import:{term}")
        if record.test:
            score += .25
        if record.generated:
            score -= 3
        if score:
            ranked.append((score, record, ",".join(reasons[:5])))
    return sorted(ranked, key=lambda x: (-x[0], x[1].path))


def _dedupe_ranked(rows):
    best = {}
    for score, record, reason in rows:
        if record.path not in best or score > best[record.path][0]:
            best[record.path] = (score, record, reason)
    return sorted(best.values(), key=lambda x: (-x[0], x[1].path))


def _dedupe_edges(rows):
    return list({(e.source, e.target, e.kind, e.reason): e for e in rows}.values())


def _unique_edges(rows):
    return tuple(_dedupe_edges(rows))


def _anchors(record: FileRecord, query: str, lines: list[str]) -> list[int]:
    terms = _terms(query)
    hits = [i for i, line in enumerate(lines) if any(t in line.lower() for t in terms)]
    if hits:
        return hits
    return [s.start_line - 1 for s in record.symbols[:3]] or [0]


def _estimate_tokens(text: str) -> int:
    # A conservative stable estimate; it is a budget guard, not a tokenizer claim.
    return max(1, len(TOKEN_RE.findall(text)) + len(text) // 24)


def render_compact(answer: RepoAnswer) -> str:
    lines = [
        f"AER-REPO-MAP v{answer.schema_version} mode={answer.mode} est_tokens={answer.token_estimate} snapshot={answer.snapshot[:12]}",
        f"files={len(answer.files)} edges={len(answer.edges)} unknowns={len(answer.unknowns)}",
    ]
    for evidence in answer.evidence:
        lines.append(f"FILE {evidence.path}:{evidence.start_line}-{evidence.end_line} score={evidence.score:.2f} reason={evidence.reason}")
        lines.extend("  " + line for line in evidence.text.splitlines())
    for edge in answer.edges:
        lines.append(f"EDGE {edge.kind} {edge.source} -> {edge.target} confidence={edge.confidence:.2f} reason={edge.reason}")
    for unknown in answer.unknowns:
        lines.append(f"UNKNOWN {unknown}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AER deterministic repository intelligence map")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--for", dest="query", default="", help="task/question to localize")
    parser.add_argument("--mode", choices=("search", "callers", "callees", "impact", "tests", "situ", "pack-task"), default="search")
    parser.add_argument("--symbol", default="", help="symbol used by callers/callees/impact modes")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--token-budget", type=int, default=4000)
    parser.add_argument("--max-files", type=int, default=12)
    parser.add_argument("--graph-depth", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    query = args.symbol or args.query
    repo = RepositoryMap.build(args.root)
    answer = repo.answer(query, mode=args.mode, token_budget=args.token_budget, max_files=args.max_files, graph_depth=args.graph_depth, base=args.base)
    print(json.dumps(answer.as_dict(), indent=2, sort_keys=True) if args.json else render_compact(answer), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
