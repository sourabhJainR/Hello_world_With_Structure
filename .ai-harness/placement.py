#!/usr/bin/env python3
"""Language-neutral code placement and naming guidance based on repository patterns."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IGNORED = {".git", ".ai-harness", ".venv", "venv", "node_modules", "bin", "obj", "dist", "build", "target"}
SOURCE_EXTENSIONS = {".py", ".cs", ".java", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"}


def _source_files() -> list[Path]:
    return [
        path for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
        and not any(part in IGNORED for part in path.parts)
    ]


def _source_dirs() -> list[Path]:
    dirs: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_dir() or any(part in IGNORED for part in path.parts):
            continue
        try:
            source_count = sum(1 for child in path.iterdir() if child.is_file() and child.suffix.lower() in SOURCE_EXTENSIONS)
        except OSError:
            continue
        if source_count >= 2:
            dirs.append(path)
    return sorted(dirs, key=lambda p: (len(p.relative_to(ROOT).parts), str(p)))[:80]


def _classify(name: str) -> str | None:
    lowered = name.lower()
    patterns = {
        "models": ("model", "models", "entity", "entities", "dto", "contract", "contracts", "schema", "schemas"),
        "interfaces": ("interface", "interfaces", "protocol", "protocols", "ports"),
        "services": ("service", "services", "usecase", "usecases"),
        "controllers": ("controller", "controllers", "handler", "handlers", "endpoint", "endpoints", "api"),
        "repositories": ("repository", "repositories", "dao", "data", "persistence"),
        "infrastructure": ("infra", "infrastructure", "adapters", "adapter", "clients", "client"),
        "utilities": ("util", "utils", "utility", "common", "helpers", "helper"),
        "constants": ("constant", "constants"),
        "tests": ("test", "tests", "spec", "specs"),
        "configuration": ("config", "configuration", "settings", "options"),
    }
    for category, needles in patterns.items():
        if lowered in needles:
            return category
    return None


def _file_category(file_name: str) -> str:
    lowered = file_name.lower()
    if "test" in lowered or "spec" in lowered:
        return "tests"
    if any(token in lowered for token in ("interface", "protocol")):
        return "interfaces"
    if "constant" in lowered or "constants" in lowered:
        return "constants"
    if any(token in lowered for token in ("config", "setting", "option")):
        return "configuration"
    if any(token in lowered for token in ("controller", "handler", "endpoint")):
        return "controllers"
    if any(token in lowered for token in ("repository", "repo", "dao")):
        return "repositories"
    if "service" in lowered:
        return "services"
    if any(token in lowered for token in ("model", "entity", "dto", "contract", "schema")):
        return "models"
    if any(token in lowered for token in ("adapter", "client", "infrastructure", "infra")):
        return "infrastructure"
    if any(token in lowered for token in ("util", "helper")):
        return "utilities"
    return "domain-or-feature"


def _split_words(stem: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", stem)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return [part for part in value.lower().split() if part]


def _naming_style(files: list[Path]) -> dict[str, Any]:
    styles = {"PascalCase": 0, "camelCase": 0, "snake_case": 0, "kebab-case": 0, "dot.case": 0}
    for path in files:
        stem = path.stem
        if re.fullmatch(r"[A-Z][A-Za-z0-9]*", stem):
            styles["PascalCase"] += 1
        elif re.fullmatch(r"[a-z][A-Za-z0-9]*", stem) and any(ch.isupper() for ch in stem):
            styles["camelCase"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", stem):
            styles["snake_case"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", stem):
            styles["kebab-case"] += 1
        elif re.fullmatch(r"[a-z0-9]+(?:\.[a-z0-9]+)+", stem):
            styles["dot.case"] += 1
    return {"detected": styles, "preferred": max(styles, key=styles.get) if any(styles.values()) else "repository-defined"}


def _matching_siblings(candidate_dir: Path, category: str) -> list[Path]:
    return sorted(
        [p for p in _source_files() if p.parent == candidate_dir and _file_category(p.name) == category],
        key=lambda p: p.name.lower(),
    )


def _closest_related(file_name: str, files: list[Path]) -> list[Path]:
    words = set(_split_words(Path(file_name).stem))
    ranked: list[tuple[int, Path]] = []
    for path in files:
        overlap = len(words & set(_split_words(path.stem)))
        if overlap:
            ranked.append((overlap, path))
    return [path for _, path in sorted(ranked, key=lambda pair: (-pair[0], str(pair[1])))[:8]]


def build_placement_plan(file_names: list[str]) -> dict[str, Any]:
    files = _source_files()
    dirs = _source_dirs()
    naming = _naming_style(files)
    classified: dict[str, list[str]] = {}
    for directory in dirs:
        category = _classify(directory.name)
        if category:
            classified.setdefault(category, []).append(str(directory.relative_to(ROOT)).replace("\\", "/"))

    recommendations: list[dict[str, Any]] = []
    for file_name in file_names:
        category = _file_category(file_name)
        candidates = classified.get(category, [])
        scored: list[tuple[float, str, str, list[str]]] = []
        for candidate in candidates:
            directory = ROOT / candidate
            siblings = _matching_siblings(directory, category)
            score = 10.0
            reasons = [f"matches existing {category} segregation"]
            related = _closest_related(file_name, siblings)
            if related:
                score += 8.0
                reasons.append(f"has {len(related)} related sibling file(s)")
            if siblings:
                score += 3.0
                reasons.append("matches established local naming/file pattern")
            scored.append((score, candidate, "primary structural candidate", reasons))

        related = _closest_related(file_name, files)
        if related:
            for path in related:
                relative = str(path.parent.relative_to(ROOT)).replace("\\", "/") or "."
                if relative not in {item[1] for item in scored}:
                    scored.append((9.0, relative, "closest related code", ["keeps new code beside semantically related code"]))

        scored.sort(key=lambda item: (-item[0], item[1]))
        if scored:
            preferred = scored[0][1]
            reason = "; ".join(scored[0][3])
        else:
            preferred = "."
            reason = "no reliable structural convention detected; place beside closest cohesive code"
            scored = [(1.0, ".", "fallback", [reason])]

        recommendations.append({
            "file": file_name,
            "category": category,
            "naming_style": naming["preferred"],
            "candidates": [
                {"path": path, "score": score, "basis": basis, "reasons": reasons}
                for score, path, basis, reasons in scored[:6]
            ],
            "preferred": preferred,
            "reason": reason,
            "placement_rule": "Prefer existing repository segregation; among multiple valid locations choose the strongest scalable and compatible local pattern.",
        })
    return {
        "repository": str(ROOT),
        "categories": classified,
        "naming": naming,
        "recommendations": recommendations,
        "decision_precedence": [
            "explicit_repository_instruction",
            "dominant_local_pattern",
            "most_advanced_scalable_compatible_local_pattern",
            "closest_cohesive_existing_location",
            "current_mainstream_ecosystem_convention_for_genuinely_new_area",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Recommend code locations and naming based on repository conventions")
    parser.add_argument("files", nargs="+", help="new file names, e.g. ExportService.py ExportConstants.py")
    args = parser.parse_args()
    print(json.dumps(build_placement_plan(args.files), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
