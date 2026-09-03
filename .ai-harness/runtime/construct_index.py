#!/usr/bin/env python3
"""Build a lightweight, dependency-free index of actual repository constructs."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
IGNORED_PREFIXES = (".git/", ".ai-harness/runs/", ".ai-harness/worktrees/", "node_modules/", ".venv/", "venv/", "bin/", "obj/", "dist/", "build/", "target/", "__pycache__/")
IGNORED_FILES = {".git"}
TEXT_EXTENSIONS = {
    ".py", ".cs", ".java", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".h", ".hpp",
    ".sql", ".json", ".yaml", ".yml", ".toml", ".xml", ".md", ".graphql", ".gql", ".proto", ".csproj", ".sln",
}

@dataclass(frozen=True)
class Construct:
    id: str
    kind: str
    name: str
    path: str
    line: int
    end_line: int | None = None
    parent: str | None = None
    signature: str | None = None
    language: str | None = None


def _ignored(path: Path) -> bool:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    return path.name in IGNORED_FILES or any(rel.startswith(prefix) for prefix in IGNORED_PREFIXES)


def _language(path: Path) -> str:
    return {".py": "python", ".cs": "csharp", ".java": "java", ".go": "go", ".rs": "rust", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript", ".kt": "kotlin", ".swift": "swift", ".rb": "ruby", ".php": "php", ".sql": "sql", ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".xml": "xml", ".graphql": "graphql", ".gql": "graphql", ".proto": "protobuf"}.get(path.suffix.lower(), "text")


def _id(kind: str, path: str, name: str, line: int) -> str:
    raw = f"{kind}|{path}|{name}|{line}".encode()
    return "rc-" + hashlib.sha1(raw).hexdigest()[:12]


def _add(result: list[Construct], kind: str, name: str, path: str, line: int, *, parent: str | None = None, signature: str | None = None, language: str | None = None) -> None:
    result.append(Construct(_id(kind, path, name, line), kind, name, path, line, None, parent, signature, language))


def _brace_end(lines: list[str], start: int) -> int | None:
    depth = 0
    seen = False
    for index in range(start, len(lines)):
        line = lines[index]
        depth += line.count("{") - line.count("}")
        if "{" in line:
            seen = True
        if seen and depth <= 0:
            return index + 1
    return None


def _scan_code(path: Path, text: str, result: list[Construct]) -> None:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    lang = _language(path)
    lines = text.splitlines()
    parents: list[tuple[int, str]] = []
    patterns: list[tuple[str, re.Pattern[str]]] = [
        ("class", re.compile(r"^\s*(?:public|private|protected|internal|abstract|final|sealed|partial|export|open|data|static|unsafe|async|\s)*\s*class\s+([A-Za-z_][\w]*)")),
        ("interface", re.compile(r"^\s*(?:public|private|protected|internal|export|\s)*\s*interface\s+([A-Za-z_][\w]*)")),
        ("record", re.compile(r"^\s*(?:public|private|protected|internal|export|\s)*\brecord(?:\s+class|\s+struct)?\s+([A-Za-z_][\w]*)")),
        ("struct", re.compile(r"^\s*(?:public|private|protected|internal|export|\s)*\bstruct\s+([A-Za-z_][\w]*)")),
        ("enum", re.compile(r"^\s*(?:public|private|protected|internal|export|\s)*\benum\s+([A-Za-z_][\w]*)")),
    ]
    for number, line in enumerate(lines, 1):
        for kind, pattern in patterns:
            match = pattern.search(line)
            if match:
                name = match.group(1)
                parent = parents[-1][1] if parents else None
                _add(result, kind, name, rel, number, parent=parent, signature=line.strip(), language=lang)
                if "{" in line:
                    end = _brace_end(lines, number - 1)
                    parents.append((end or len(lines), name))
                break
        while parents and number > parents[-1][0]:
            parents.pop()

    function_patterns = {
        "python": re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][\w]*)\s*\((.*?)\)"),
        "go": re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][\w]*)\s*\("),
        "rust": re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][\w]*)\s*\("),
        "csharp": re.compile(r"^\s*(?:(?:public|private|protected|internal|static|async|virtual|override|sealed|new|partial|unsafe|extern)\s+)*(?:[\w<>,.?\[\]]+)\s+([A-Za-z_][\w]*)\s*\("),
        "java": re.compile(r"^\s*(?:(?:public|private|protected|static|final|synchronized|abstract|native|default)\s+)*[\w<>,.?\[\]]+\s+([A-Za-z_][\w]*)\s*\("),
        "typescript": re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][\w]*)\s*\(|^\s*(?:public|private|protected|static|async|get|set)?\s*([A-Za-z_][\w]*)\s*\([^;]*\)\s*[:{]"),
        "javascript": re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][\w]*)\s*\(|^\s*(?:async\s+)?([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?\("),
        "kotlin": re.compile(r"^\s*(?:public|private|protected|internal|suspend|inline|override|open|final|operator|infix|tailrec|\s)*fun\s+([A-Za-z_][\w]*)\s*\("),
        "swift": re.compile(r"^\s*(?:public|private|internal|fileprivate|open|static|class|override|mutating|nonmutating|final|\s)*func\s+([A-Za-z_][\w]*)\s*\("),
        "ruby": re.compile(r"^\s*def\s+([A-Za-z_][\w!?=]*)"),
        "php": re.compile(r"^\s*(?:public|private|protected|static|final)?\s*function\s+([A-Za-z_][\w]*)\s*\("),
    }
    pattern = function_patterns.get(lang)
    if pattern:
        for number, line in enumerate(lines, 1):
            match = pattern.search(line)
            if match:
                name = next((group for group in match.groups() if group), None)
                if name and name not in {"if", "for", "while", "switch", "catch"}:
                    parent = None
                    for construct in reversed(result):
                        if construct.path == rel and construct.line <= number and construct.kind in {"class", "interface", "record", "struct", "enum"}:
                            parent = construct.name
                            break
                    _add(result, "function", name, rel, number, parent=parent, signature=line.strip(), language=lang)


def _scan_sql(path: Path, text: str, result: list[Construct]) -> None:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    for number, line in enumerate(text.splitlines(), 1):
        patterns = [
            ("stored_procedure", r"\b(?:CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?PROCEDURE\s+([\[\]\w.]+)"),
            ("view", r"\b(?:CREATE|ALTER)\s+VIEW\s+([\[\]\w.]+)"),
            ("table", r"\b(?:CREATE|ALTER)\s+TABLE\s+([\[\]\w.]+)"),
            ("function", r"\b(?:CREATE|ALTER)\s+FUNCTION\s+([\[\]\w.]+)"),
        ]
        for kind, expression in patterns:
            match = re.search(expression, line, re.I)
            if match:
                _add(result, kind, match.group(1).strip("[]"), rel, number, signature=line.strip(), language="sql")


def _scan_data(path: Path, text: str, result: list[Construct]) -> None:
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return
        if isinstance(value, dict):
            for key in value:
                _add(result, "json_property", key, rel, 1, language="json")
    elif suffix in {".yaml", ".yml", ".toml"}:
        for number, line in enumerate(text.splitlines(), 1):
            match = re.match(r"^\s*([A-Za-z_][\w.-]*)\s*(?:=|:)", line)
            if match:
                _add(result, "config_key", match.group(1), rel, number, signature=line.strip(), language="yaml" if suffix != ".toml" else "toml")


def build_index(root: Path = ROOT) -> dict[str, Any]:
    constructs: list[Construct] = []
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS or _ignored(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files += 1
        if path.suffix.lower() == ".sql":
            _scan_sql(path, text, constructs)
        elif path.suffix.lower() in {".json", ".yaml", ".yml", ".toml"}:
            _scan_data(path, text, constructs)
        else:
            _scan_code(path, text, constructs)
    return {"schema_version": 1, "root": str(root), "files_scanned": files, "construct_count": len(constructs), "constructs": [asdict(item) for item in constructs]}


def compact_index(index: dict[str, Any], limit: int = 9000) -> str:
    """Create prompt-sized construct references without losing exact paths/symbols."""
    lines = ["# Repository Construct Index", f"Files scanned: {index.get('files_scanned', 0)}", f"Constructs indexed: {index.get('construct_count', 0)}"]
    for item in index.get("constructs", []):
        parent = f" parent={item['parent']}" if item.get("parent") else ""
        signature = f" | {item['signature']}" if item.get("signature") else ""
        lines.append(f"- [{item['id']}] {item['kind']} {item['path']}:{item['line']}::{item['name']}{parent}{signature}")
    text = "\n".join(lines)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 80)] + "\n... [construct index compacted; full index is regenerated from the repository source]"


def validate_references(text: str, index: dict[str, Any]) -> dict[str, Any]:
    """Check explicit repository references against indexed constructs/files."""
    known_paths = {str(item["path"]) for item in index.get("constructs", [])}
    known_ids = {str(item["id"]) for item in index.get("constructs", [])}
    known_symbols = {(str(item["path"]), str(item["name"])) for item in index.get("constructs", [])}
    references = []
    unresolved = []
    pattern = re.compile(r"(?:\[?(rc-[a-f0-9]{12})\]?|([\w./\\-]+\.(?:py|cs|java|go|rs|ts|tsx|js|jsx|kt|swift|rb|php|c|cpp|h|hpp|sql|json|yaml|yml|toml|xml))(?::(\d+))?(?:::([A-Za-z_][\w]*))?)")
    for match in pattern.finditer(text):
        construct_id, path, line, name = match.groups()
        if construct_id:
            references.append(construct_id)
            if construct_id not in known_ids:
                unresolved.append(construct_id)
        elif path and path in known_paths:
            references.append(f"{path}:{line or ''}::{name or ''}".rstrip(":"))
            if name and (path, name) not in known_symbols:
                unresolved.append(f"{path}::{name}")
    return {"reference_count": len(references), "unresolved": sorted(set(unresolved)), "passed": not unresolved}
