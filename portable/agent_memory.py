"""Small local memory owned by an individual agent during a run.

This is deliberately separate from shared learning. The execution agent can keep
its own working notes without turning them into team knowledge. Cross-agent
lessons are promoted only by the learning steward.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any


class AgentMemory:
    """Bounded agent-private session memory."""

    def __init__(self, root: Path, agent: str, *, max_entries: int = 32, max_chars: int = 12000) -> None:
        if max_entries < 1 or max_chars < 1:
            raise ValueError("agent memory budgets must be positive")
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", agent).strip("._") or "agent"
        self.path = Path(root) / ".ai-harness" / "agent-memory" / f"{safe}.jsonl"
        self.max_entries = max_entries
        self.max_chars = max_chars
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows[-self.max_entries:]

    def read(self, limit: int = 5000) -> str:
        rows = self.snapshot()
        text = "\n".join(str(row.get("text", "")).strip() for row in rows if str(row.get("text", "")).strip())
        if len(text) <= limit:
            return text
        return text[: max(200, limit - 50)] + "\n...[agent memory compacted]"

    def remember(self, text: str, *, kind: str = "note") -> None:
        clean = str(text).strip()
        if not clean:
            return
        row = {"kind": kind, "text": clean[:2000], "recorded_at": int(time.time())}
        rows = self.snapshot()
        rows.append(row)
        while rows and len(rows) > self.max_entries:
            rows.pop(0)
        while rows and sum(len(json.dumps(x, ensure_ascii=False)) + 1 for x in rows) > self.max_chars:
            rows.pop(0)
        self.path.write_text("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in rows) + ("\n" if rows else ""), encoding="utf-8")


__all__ = ["AgentMemory"]
