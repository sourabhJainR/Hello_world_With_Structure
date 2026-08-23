#!/usr/bin/env python3
"""Language-neutral code placement guidance based on repository structure."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IGNORED = {".git", ".ai-harness", ".venv", "venv", "node_modules", "bin", "obj", "dist", "build", "target"}


def _source_dirs() -> list[Path]:
    dirs: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_dir() or any(part in IGNORED for part in path.parts):
            continue
        source_count = sum(1 for child in path.iterdir() if child.is_file() and child.suffix.lower() in {".py", ".cs", ".java", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"})
        if source_count >= 2:
            dirs.append(path)
    return sorted(dirs, key=lambda p: (len(p.parts), str(p)))[:40]


def _classify(name: str) -> str | None:
    lowered = name.lower()
    patterns = {
        "models": ("model", "entity", "entities", "dto", "contract", "schema"),
        "interfaces": ("interface", "protocol", "ports"),
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
        if lowered in needles or any(lowered.endswith(needle) for needle in needles):
            return category
    return None


def _file_category(file_name: str) -> str:
    lowered = file_name.lower()
    if "test" in lowered or lowered.endswith(("_spec.py", ".spec.ts", ".test.ts", ".test.js")):
        return "tests"
    if any(token in lowered for token in ("interface", "protocol")):
        return "interfaces"
    if "constant" in lowered or lowered.endswith(("constants.py", "constants.ts", "constants.cs")):
        return "constants"
    if any(token in lowered for token in ("config", "setting", "option")):
        return "configuration"
    if any(token in lowered for token in ("controller", "handler", "endpoint")):
        return "controllers"
    if any(token in lowered for token in ("repository", "dao")):
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


def build_placement_plan(file_names: list[str]) -> dict[str, Any]:
    dirs = _source_dirs()
    classified: dict[str, list[str]] = {}
    for directory in dirs:
        category = _classify(directory.name)
        if category:
            classified.setdefault(category, []).append(str(directory.relative_to(ROOT)).replace("\\", "/"))

    recommendations: list[dict[str, Any]] = []
    for file_name in file_names:
        category = _file_category(file_name)
        candidates = classified.get(category, [])
        reason = f"matches existing {category} segregation"
        if not candidates:
            feature_candidates = [str(path.relative_to(ROOT)).replace("\\", "/") for path in dirs if path.name.lower() in {Path(file_name).stem.lower(), "domain", "core", "application", "features", "shared"}]
            candidates = feature_candidates[:5]
            if candidates:
                reason = "no dedicated category found; prefers closest existing feature/domain boundary"
        if not candidates:
            candidates = ["existing feature/module directory containing the closest related code"]
            reason = "no reliable structural convention detected; place beside the closest cohesive related code and avoid creating a new layer"
        recommendations.append({"file": file_name, "category": category, "candidates": candidates, "preferred": candidates[0], "reason": reason})
    return {"repository": str(ROOT), "categories": classified, "recommendations": recommendations}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Recommend code locations based on repository segregation")
    parser.add_argument("files", nargs="+", help="new file names, e.g. ExportService.py ExportConstants.py")
    args = parser.parse_args()
    print(json.dumps(build_placement_plan(args.files), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
