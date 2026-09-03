#!/usr/bin/env python3
"""Provider-neutral code knowledge fabric plus local compatibility and task memory."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from runtime.legacy_compatibility import build_compatibility_profile, compatibility_instructions
from runtime import task_memory

ROOT = Path(__file__).resolve().parent.parent


def _run(command: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 124, str(exc)
    return result.returncode, (result.stdout or result.stderr).strip()


def available(config: dict[str, Any]) -> dict[str, bool]:
    knowledge = config.get("knowledge", {})
    return {"graphify": bool(knowledge.get("graphify", {}).get("enabled", False) and shutil.which("graphify")), "code_memory": bool(knowledge.get("code_memory", {}).get("enabled", False) and shutil.which("codebase-memory-mcp")), "graph_artifact": any((ROOT / candidate).exists() for candidate in ("graphify-out/graph.json", ".graphify/graph.json", ".codebase-memory/graph.json")), "semantic_reranker": bool(knowledge.get("semantic_reranker", {}).get("enabled", False))}


def _query_graphify(task: str, timeout: int = 20) -> dict[str, Any]:
    code, output = _run(["graphify", "query", task], timeout); return {"source": "graphify", "exit_code": code, "output": output[:12000]}


def _query_code_memory(task: str, timeout: int = 20) -> dict[str, Any]:
    code, output = _run(["codebase-memory-mcp", "cli", "semantic_query", "--project", ROOT.name, "--query", task], timeout)
    if code != 0: code, output = _run(["codebase-memory-mcp", "cli", "search_graph", "--project", ROOT.name, "--name-pattern", ".*"], timeout)
    return {"source": "codebase-memory-mcp", "exit_code": code, "output": output[:12000]}


def _read_graph_artifact(task: str, limit: int = 80) -> dict[str, Any]:
    candidates = (ROOT / "graphify-out/graph.json", ROOT / ".graphify/graph.json", ROOT / ".codebase-memory/graph.json")
    path = next((item for item in candidates if item.exists()), None)
    if path is None: return {"source": "graph-artifact", "output": ""}
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return {"source": "graph-artifact", "output": f"unreadable: {exc}"}
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", task.lower())); nodes = data.get("nodes", []) if isinstance(data, dict) else []; ranked = []
    for node in nodes:
        if not isinstance(node, dict): continue
        text = " ".join(str(node.get(k, "")) for k in ("id", "name", "label", "type", "path")); overlap = len(words & set(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text.lower()))); ranked.append((overlap, text))
    ranked.sort(reverse=True); return {"source": "graph-artifact", "output": "\n".join(text for _, text in ranked[:limit])}


def collect(task: str, config: dict[str, Any]) -> dict[str, Any]:
    """Collect bounded structural evidence; never installs or mutates external tools."""
    status = available(config); sources: list[dict[str, Any]] = []
    if status["graphify"]: sources.append(_query_graphify(task))
    if status["code_memory"]: sources.append(_query_code_memory(task))
    if status["graph_artifact"]: sources.append(_read_graph_artifact(task))
    evidence: list[str] = []
    for source in sources:
        output = str(source.get("output", "")).strip()
        if output: evidence.append(f"[{source['source']}]\n{output}")
    if not sources:
        evidence.append("No external structural or historical knowledge source available.")
    compatibility = build_compatibility_profile(ROOT); evidence.append(compatibility_instructions(compatibility)); evidence.append(task_memory.guidance(ROOT, task))
    budget = int(config.get("knowledge", {}).get("budget_chars", 6000)); joined = "\n\n".join(evidence)[:budget]
    # ``sources`` is reserved for external knowledge providers/artifacts. Local
    # compatibility and task-memory evidence is deterministic harness context,
    # not an external source. Keep its provenance in the evidence payload.
    return {"available": status, "sources": [item["source"] for item in sources], "evidence": joined or "No external structural or historical knowledge source available.", "strategy": "construct index + language-version constraints + historical task evidence + AST/graph retrieval + targeted reads + verification"}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Collect local code knowledge for an AI coding task"); parser.add_argument("task"); args = parser.parse_args()
    result = collect(args.task, {"knowledge": {"graphify": {"enabled": True}, "code_memory": {"enabled": True}}}); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
