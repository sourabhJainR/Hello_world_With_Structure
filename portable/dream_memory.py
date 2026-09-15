"""Post-run dreaming for safe, portable long-term learning.

Dreaming is deliberately outside the execution graph. It reads the durable
observation ledger, clusters repeated outcomes, and writes only curated,
versioned learnings back through the memory API. Execution agents never carry
this analysis in their working context.
"""
from __future__ import annotations

import hashlib
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
                "|".join(str(x or "").strip().lower() for x in (row[1], row[2], row[3], row[5], row[6])).encode("utf-8")
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

    @staticmethod
    def _evidence(observations: list[dict[str, Any]]) -> list[str]:
        values: set[str] = set()
        for observation in observations:
            raw = observation.get("evidence_ids") or "[]"
            try:
                import json
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                values.update(str(x).strip() for x in parsed if str(x).strip())
            except (TypeError, ValueError):
                values.update(x.strip() for x in str(raw).split(",") if x.strip())
        return sorted(values)

    def dream(self, task: str) -> list[dict[str, Any]]:
        """Promote repeated, evidence-backed observations into durable learning.

        A lesson becomes reusable only after independent observations agree on
        the outcome. Mixed outcomes stay candidates so one bad promotion cannot
        poison future runs. The operation is idempotent through the ledger's
        fingerprinting and concurrency transaction.
        """
        promoted: list[dict[str, Any]] = []
        for _, observations in self._candidate_groups(task):
            if len(observations) < self.min_repeat:
                continue
            outcomes = {str(x["outcome"]) for x in observations}
            if outcomes == {"worked"}:
                outcome = "worked"
                lesson = "Repeated success across {} observations: {}".format(len(observations), observations[0]["detail"])
            elif outcomes.issubset({"failed", "regressed"}):
                outcome = "regressed" if "regressed" in outcomes else "failed"
                lesson = "Repeated unsuccessful approach across {} observations: {}".format(len(observations), observations[0]["detail"])
            else:
                continue
            representative = observations[0]
            promoted.append(record(
                self.root,
                task=representative["task"], category=representative["category"],
                outcome=outcome, detail=lesson, command=representative["command"],
                approach=representative["approach"], run_id=representative["run_id"],
                evidence_ids=self._evidence(observations), source_agent="dream-cycle",
                promotion="verified",
            ))
        return promoted

    def status(self) -> dict[str, Any]:
        dbp = _db_path(self.root)
        with _process_lock(dbp.with_name("task-memory.lock")):
            with _connect(self.root) as db:
                counts = dict(db.execute("SELECT promotion,COUNT(*) FROM observations GROUP BY promotion").fetchall())
        return {"counts": counts, "generated_at": int(time.time()), "min_repeat": self.min_repeat}


__all__ = ["DreamMemory"]
