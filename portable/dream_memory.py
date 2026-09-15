"""Post-run dreaming for safe, portable long-term learning.

Dreaming is deliberately outside the execution graph. It reads the durable
observation ledger, clusters repeated outcomes, and writes only curated,
versioned learnings back through the memory API. Execution agents never carry
this analysis in their working context.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

from runtime.task_memory import _connect, _db_path, _process_lock, record


class DreamMemory:
    """Curate observations after a run without polluting execution context."""

    MIN_REPEAT = 2

    def __init__(self, root: Path, *, min_repeat: int = MIN_REPEAT) -> None:
        self.root = Path(root)
        self.min_repeat = max(2, int(min_repeat))

    def _candidate_groups(self, task: str) -> list[tuple[str, list[dict[str, Any]]]]:
        dbp = _db_path(self.root)
        groups: dict[str, list[dict[str, Any]]] = {}
        with _process_lock(dbp.with_name("task-memory.lock")):
            with _connect(self.root) as db:
                rows = db.execute(
                    """SELECT id,task,category,outcome,detail,command,approach,evidence_ids,
                              run_id,promotion,learning_version,revision,source_agent
                       FROM observations
                       WHERE task=? AND promotion IN ('candidate','verified')
                       ORDER BY recorded_at DESC""",
                    (str(task).strip(),),
                ).fetchall()
        for row in rows:
            key = hashlib.sha256(
                "|".join(str(x or "").strip().lower() for x in row[1:7]).encode("utf-8")
            ).hexdigest()
            groups.setdefault(key, []).append(
                {
                    "id": row[0], "task": row[1], "category": row[2],
                    "outcome": row[3], "detail": row[4], "command": row[5],
                    "approach": row[6], "evidence_ids": row[7], "run_id": row[8],
                    "promotion": row[9], "learning_version": row[10],
                    "revision": row[11], "source_agent": row[12],
                }
            )
        return list(groups.items())

    def dream(self, task: str) -> list[dict[str, Any]]:
        """Promote repeated, evidence-backed observations into durable learning.

        This is intentionally deterministic. A future model may improve the
        analysis, but memory safety and promotion rules do not depend on model
        quality or provider-specific behavior.
        """
        promoted: list[dict[str, Any]] = []
        for _, observations in self._candidate_groups(task):
            if len(observations) < self.min_repeat:
                continue
            outcomes = {str(x["outcome"]) for x in observations}
            if outcomes != {"worked"}:
                continue
            evidence = sorted({e for x in observations for e in str(x["evidence_ids"] or "").split(",") if e.strip()})
            representative = observations[0]
            detail = (
                f"Repeated success across {len(observations)} observations: "
                f"{representative['detail']}"
            )
            promoted.append(record(
                self.root,
                task=representative["task"],
                category=representative["category"],
                outcome="worked",
                detail=detail,
                command=representative["command"],
                approach=representative["approach"],
                run_id=representative["run_id"],
                evidence_ids=evidence,
                source_agent="dream-cycle",
                promotion="verified",
            ))
        return promoted

    def status(self) -> dict[str, Any]:
        dbp = _db_path(self.root)
        with _process_lock(dbp.with_name("task-memory.lock")):
            with _connect(self.root) as db:
                counts = dict(db.execute(
                    "SELECT promotion,COUNT(*) FROM observations GROUP BY promotion"
                ).fetchall())
        return {"counts": counts, "generated_at": int(time.time()), "min_repeat": self.min_repeat}


__all__ = ["DreamMemory"]
