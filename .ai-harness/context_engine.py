"""Deterministic, IO-aware context selection for AI coding runs.

Inspired by the IO-awareness of FlashAttention and the practical context-engineering patterns in
modern coding-agent harnesses: keep stable context small, retrieve targeted evidence, compact old
history before the model boundary, and preserve correctness-critical state.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

_STOP = {"the", "and", "for", "with", "from", "this", "that", "into", "have", "will", "task", "change", "please", "need", "make", "using"}
_PRIORITY = (
    ("critical", 6.0),
    ("acceptance", 6.0),
    ("constraint", 5.0),
    ("protected", 5.0),
    ("decision", 5.0),
    ("evidence", 5.0),
    ("verification", 5.0),
    ("regression", 5.0),
    ("risk", 4.5),
    ("root cause", 4.5),
    ("failed", 4.0),
    ("next", 3.5),
    ("changed", 3.0),
    ("file", 1.0),
)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()) if w not in _STOP}


def _rank_file(name: str, task_words: set[str]) -> float:
    words = _words(name.replace("/", " "))
    score = len(words & task_words) * 5
    lowered = name.lower()
    for marker, weight in (("test", 1.0), ("readme", 0.5), ("docs", 0.5), ("config", 1.5), ("src/", 1.0), ("lib/", 1.0)):
        if marker in lowered:
            score += weight
    return score


def build_repository_context(root: Path, task: str, limit_files: int = 180, budget_chars: int = 9000) -> str:
    try:
        result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False, timeout=30)
        if result.returncode != 0:
            return "# Repository Context\nUnavailable: git ls-files failed."
        files = [line for line in result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return "# Repository Context\nUnavailable: repository enumeration failed."

    task_words = _words(task)
    ranked = sorted(files, key=lambda item: (-_rank_file(item, task_words), item))
    selected = ranked[:limit_files]

    top_level: dict[str, list[str]] = {}
    for name in selected:
        parts = Path(name).parts
        bucket = parts[0] if parts else "."
        top_level.setdefault(bucket, []).append(name)

    lines = ["# Repository Context", "", "## Stable structure"]
    used = 0
    for bucket in sorted(top_level):
        entry = f"- {bucket}/ ({len(top_level[bucket])} relevant files)"
        if used + len(entry) + 1 > budget_chars:
            break
        lines.append(entry)
        used += len(entry) + 1

    lines.extend(["", "## Relevant files"])
    for name in selected:
        entry = f"- {name}"
        if used + len(entry) + 1 > budget_chars:
            break
        lines.append(entry)
        used += len(entry) + 1

    return "\n".join(lines) + "\n"


def compact_history(history: str, task: str, budget_chars: int) -> str:
    """Compress history by information value, retaining proof and task-critical state first.

    This is deliberately deterministic and model-free. It does not invent summaries. It removes
    repeated low-value lines and keeps the highest-value evidence, with a small recent tail so the
    current execution state remains visible. That gives the caller a predictable token ceiling.
    """
    if budget_chars <= 0 or not history.strip():
        return ""
    lines = [line.strip() for line in history.splitlines() if line.strip()]
    task_words = _words(task)
    candidates: list[tuple[float, int, str]] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        normalized = re.sub(r"\s+", " ", line.lower())
        if normalized in seen:
            continue
        seen.add(normalized)
        score = len(_words(line) & task_words) * 2.0
        for marker, weight in _PRIORITY:
            if marker in normalized:
                score += weight
        # Recent lines receive a small tie-breaker, never enough to displace strong proof.
        score += index / max(1, len(lines))
        candidates.append((score, index, line))

    candidates.sort(key=lambda item: (-item[0], -item[1]))
    selected: list[tuple[int, str]] = []
    used = 0
    for _, index, line in candidates:
        entry_size = len(line) + 1
        if used + entry_size > budget_chars:
            continue
        selected.append((index, line))
        used += entry_size

    # Always try to retain the most recent line when budget permits.
    if lines:
        recent = lines[-1]
        if recent not in {line for _, line in selected} and used + len(recent) + 1 <= budget_chars:
            selected.append((len(lines) - 1, recent))
    selected.sort(key=lambda item: item[0])
    return "\n".join(line for _, line in selected)


def select_context(task: str, repo_map: str, memory: str, history: str, budget_chars: int = 12000) -> dict[str, Any]:
    """Build a compact context tile set while preserving high-value evidence."""
    task_words = _words(task)

    def rank_lines(text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return sorted(lines, key=lambda line: (-len(_words(line) & task_words), -len(line)))

    memory_lines = rank_lines(memory)
    history_budget = max(1200, budget_chars // 5)
    compressed_history = compact_history(history, task, history_budget)
    history_lines = rank_lines(compressed_history)
    sections: list[tuple[str, list[str], int]] = [
        ("memory", memory_lines, max(1200, budget_chars // 6)),
        ("history", history_lines, history_budget),
    ]
    output: dict[str, str] = {}
    remaining = budget_chars
    output["repository"] = repo_map[: min(len(repo_map), remaining // 2)]
    remaining -= len(output["repository"])
    for name, lines, cap in sections:
        take = "\n".join(lines)
        take = take[: min(len(take), cap, remaining)]
        value = take or "None."
        if len(value) > remaining:
            value = value[:remaining]
        output[name] = value
        remaining -= len(value)

    return {
        "repository": output["repository"],
        "memory": output["memory"],
        "history": output["history"],
        "budget_chars": budget_chars,
        "selected": {name: len(value) for name, value in output.items()},
        "history_compression": {
            "input_chars": len(history),
            "output_chars": len(compressed_history),
            "ratio": round(len(compressed_history) / max(1, len(history)), 4),
        },
        "strategy": "stable-prefix + evidence-priority-compaction + tiled-context + relevance-ranking + bounded-evidence",
    }


def flash_context_prompt(task: str, repo_map: str, memory: str, history: str, budget_chars: int = 12000) -> tuple[str, str, str, str]:
    selected = select_context(task, repo_map, memory, history, budget_chars)
    metadata = json.dumps(
        {
            "strategy": selected["strategy"],
            "budget_chars": budget_chars,
            "selected_chars": selected["selected"],
            "history_compression": selected["history_compression"],
        },
        ensure_ascii=False,
    )
    return selected["repository"], selected["memory"], selected["history"], metadata
