"""Dependency-aware change impact analysis for human review.

The analyzer is intentionally deterministic. It does not decide whether a
change is safe; it identifies the surfaces a developer should inspect before
an agent is allowed to proceed.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

COMMON_NAMES = {
    "common", "shared", "core", "utils", "util", "helpers", "helper",
    "base", "interfaces", "interface", "contracts", "contract", "schema", "schemas",
    "models", "types", "config", "configuration", "constants", "extensions",
}
COMMON_FILE_PATTERNS = (
    re.compile(r"(^|/)(shared|common|core|utils?|helpers?|base)(/|$)", re.I),
    re.compile(r"(^|/)(interfaces?|contracts?|schemas?|types?|models?)(/|$)", re.I),
    re.compile(r"(^|/)(config|configuration|constants?)(/|$)", re.I),
)


@dataclass(frozen=True)
class ImpactRecord:
    path: str
    direct: bool
    shared: bool
    inbound_references: tuple[str, ...] = ()
    outbound_references: tuple[str, ...] = ()
    review_level: str = "normal"
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImpactReport:
    changed: tuple[str, ...]
    impacted: tuple[ImpactRecord, ...]
    review_required: bool
    review_focus: tuple[str, ...]
    suggested_tests: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _normal(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_shared(rel: str, inbound_count: int = 0) -> bool:
    parts = Path(rel).parts
    return (
        any(part.lower() in COMMON_NAMES for part in parts)
        or any(pattern.search(rel) for pattern in COMMON_FILE_PATTERNS)
        or inbound_count >= 2
    )


def _python_edges(path: Path, root: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.replace(".", "/") for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.replace(".", "/"))
    return result


def _text_edges(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    pattern = r"(?:from|import|require\(|include\()[\s\"']+([^\s\"']+)"
    return set(re.findall(pattern, text))


def _candidate_matches(reference: str, rel: str) -> bool:
    """Match an explicit module/path reference without same-filename guesses."""
    ref = reference.replace("\\", "/").lstrip("./")
    target = rel.rsplit(".", 1)[0] if "." in rel else rel
    target = target.replace("\\", "/")
    if ref == target or ref.endswith("/" + target) or target.endswith("/" + ref):
        return True

    # Python relative imports often omit the .py suffix; accept an exact stem
    # only when it maps uniquely to one repository file.
    target_name = Path(target).name
    ref_name = Path(ref).name
    if ref_name != target_name:
        return False
    return False


def _reference_index(files: list[Path], root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    references: dict[str, set[str]] = {_normal(path, root): set() for path in files}
    reverse: dict[str, set[str]] = {_normal(path, root): set() for path in files}
    for path in files:
        rel = _normal(path, root)
        refs = _python_edges(path, root) if path.suffix == ".py" else _text_edges(path)
        references[rel] = refs
    for rel, refs in references.items():
        for candidate in reverse:
            if candidate != rel and any(_candidate_matches(ref, candidate) for ref in refs):
                reverse[candidate].add(rel)
    return references, reverse


def analyze(root: Path | str, changed_paths: Iterable[str | Path]) -> ImpactReport:
    root = Path(root).resolve()
    changed = tuple(sorted({
        _normal(Path(p) if Path(p).is_absolute() else root / p, root)
        for p in changed_paths
    }))
    files = [
        path for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    references, reverse = _reference_index(files, root)

    impacted: dict[str, ImpactRecord] = {}
    queue = list(changed)
    seen = set(changed)
    while queue:
        current = queue.pop(0)
        inbound = tuple(sorted(reverse.get(current, set())))
        outbound = tuple(sorted(r for r in references.get(current, set()) if r in references))
        shared = _is_shared(current, len(inbound))
        reasons = ["explicitly changed"] if current in changed else ["references a changed path"]
        if shared:
            reasons.append("shared/common surface")
        level = "critical" if shared and inbound else ("high" if shared or inbound else "normal")
        impacted[current] = ImpactRecord(
            current,
            current in changed,
            shared,
            inbound,
            outbound,
            level,
            tuple(reasons),
        )
        for dependent in inbound:
            if dependent not in seen:
                seen.add(dependent)
                queue.append(dependent)

    shared_paths = sorted(record.path for record in impacted.values() if record.shared)
    focus = ["Review all direct changes before dependent changes."]
    if shared_paths:
        focus.append("Review shared/common paths with owners before approval: " + ", ".join(shared_paths))
        focus.append("Check public contracts, compatibility, configuration, and cross-module consumers.")
    tests = ["Run focused tests for every directly changed component."]
    if shared_paths:
        tests.extend([
            "Run tests for inbound consumers of shared paths.",
            "Run the broad regression suite before promotion.",
        ])
    warnings: list[str] = []
    if len(changed) > 10:
        warnings.append("Large change surface: split the work into smaller reviewable tasks when possible.")
    if any(record.review_level == "critical" for record in impacted.values()):
        warnings.append("Human review is required before merging a critical shared-path change.")
    return ImpactReport(
        changed,
        tuple(sorted(impacted.values(), key=lambda record: (record.review_level, record.path), reverse=True)),
        bool(shared_paths),
        tuple(focus),
        tuple(tests),
        tuple(warnings),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Analyze change impact and shared-path review requirements")
    parser.add_argument("paths", nargs="+", help="changed repository-relative paths")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(analyze(args.root, args.paths).to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
