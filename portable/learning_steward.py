"""Cross-agent learning extraction kept outside task execution."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from runtime.task_memory import record


@dataclass(frozen=True)
class Learning:
    outcome: str
    detail: str
    approach: str = ""
    command: str = ""


class LearningSteward:
    """Turn explicit steward output into durable, evidence-backed observations."""

    _line = re.compile(r"^-\s*(worked|failed|partial|regressed|not-applicable)\s*\|\s*(.*?)\s*\|\s*(.*)$", re.I)

    def __init__(self, root: Path, *, run_id: str, task: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.task = task

    def extract(self, output: str) -> list[Learning]:
        in_section = False
        found: list[Learning] = []
        for raw in str(output).splitlines():
            line = raw.strip()
            if line.lower().startswith("## learnings") or line.lower().startswith("## lessons"):
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if not in_section:
                continue
            match = self._line.match(line)
            if match:
                outcome, approach, detail = match.groups()
                if detail.strip():
                    found.append(Learning(outcome.lower(), detail.strip(), approach.strip()))
        return found

    def persist(self, output: str, *, evidence_ids: Iterable[str] = ()) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for learning in self.extract(output):
            rows.append(record(self.root, task=self.task, category="approach", outcome=learning.outcome,
                               detail=learning.detail, approach=learning.approach or None,
                               run_id=self.run_id, evidence_ids=list(evidence_ids)))
        return rows

    @staticmethod
    def prompt() -> str:
        return """## Learning steward contract
You are not an execution agent. Do not modify the task. Review the supplied agent outcomes and capture only reusable lessons that can prevent future agents from repeating a mistake or help them reproduce a verified success.

Return a short `## LEARNINGS` section using exactly:
- worked | <approach> | <reusable lesson>
- failed | <approach> | <what failed and why>
- partial | <approach> | <what remains unsafe or incomplete>
- regressed | <approach> | <regression and evidence>

Record only evidence-backed observations. Do not turn guesses, generic advice, or one-off task details into team memory. The execution agents stay focused on execution; you own this learning/peripheral work.
"""


__all__ = ["Learning", "LearningSteward"]
