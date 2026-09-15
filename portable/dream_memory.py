"""Post-run dreaming for safe, portable collective learning.

Dreaming is deliberately outside the execution graph. It reads durable
observations, detects repeated successes and failures, and creates a verified
revision only when independent runs agree. The execution agents never carry
this analysis in their working context.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from runtime.task_memory import _connect, _db_path, _process_lock, revise


class DreamMemory:
    """Curate observations into reusable patterns after execution."""

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
                    """SELECT * FROM observations
                       WHERE task=? AND promotion='candidate'
                       ORDER BY recorded_at DESC""",
                    (str(task).strip(),),
                ).fetchall()
        for raw in rows:
            # The logical key deliberately ignores detail/evidence. This lets
            # independent observations of the same approach accumulate without
            # copying every execution's transcript into the learning store.
            key = str(raw[20] or "")
            if not key:
                key = f"legacy:{raw[2]}|{raw[3]}|{raw[6] or ''}|{raw[7] or ''}"
            groups.setdefault(key, []).append({
                "id": raw[0], "task": raw[2], "category": raw[3], "outcome": raw[4],
                "detail": raw[5], "command": raw[6], "approach": raw[7],
                "construct_refs": json.loads(raw[8] or "[]"), "run_id": raw[9],
                "evidence_ids": json.loads(raw[10] or "[]"), "promotion": raw[12],
                "revision": raw[15], "learning_key": key,
            })
        return list(groups.items())

    @staticmethod
    def _independent_runs(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Only count distinct runs; retries in one run are not new evidence."""
        by_run: dict[str, dict[str, Any]] = {}
        for observation in observations:
            run = str(observation.get("run_id") or observation.get("id"))
            by_run.setdefault(run, observation)
        return list(by_run.values())

    @staticmethod
    def _evidence(observations: list[dict[str, Any]]) -> list[str]:
        values: set[str] = set()
        for observation in observations:
            values.update(str(x).strip() for x in observation.get("evidence_ids", []) if str(x).strip())
        return sorted(values)

    def dream(self, task: str) -> list[dict[str, Any]]:
        """Promote repeated independent observations into collective knowledge.

        Successes become reusable patterns. Repeated failures/regressions become
        explicit anti-patterns that future agents see first. Mixed outcomes are
        deliberately left as candidates. Promotion creates a new immutable
        revision and supersedes the observations it consolidates, preserving the
        full history for audit and future re-evaluation.
        """
        curated: list[dict[str, Any]] = []
        for _, observations in self._candidate_groups(task):
            independent = self._independent_runs(observations)
            if len(independent) < self.min_repeat:
                continue
            outcomes = {str(item["outcome"]) for item in independent}
            if outcomes == {"worked"}:
                outcome = "worked"
                prefix = "VERIFIED PATTERN"
                lesson = f"Repeated success across {len(independent)} independent runs: {independent[0]['detail']}"
            elif outcomes.issubset({"failed", "regressed"}):
                outcome = "regressed" if "regressed" in outcomes else "failed"
                prefix = "VERIFIED ANTI-PATTERN"
                lesson = f"Repeated unsuccessful approach across {len(independent)} independent runs. Avoid unless current evidence disproves it: {independent[0]['detail']}"
            else:
                # Conflicting evidence must never be promoted automatically.
                continue
            representative = independent[0]
            try:
                curated.append(revise(
                    self.root,
                    representative["id"],
                    outcome=outcome,
                    detail=f"{prefix}: {lesson}",
                    promotion="verified",
                    evidence_ids=self._evidence(independent),
                    source_agent="dream-cycle",
                ))
            except KeyError:
                # Another process may have curated the same group first.
                continue
        return curated

    def status(self) -> dict[str, Any]:
        dbp = _db_path(self.root)
        with _process_lock(dbp.with_name("task-memory.lock")):
            with _connect(self.root) as db:
                counts = dict(db.execute("SELECT promotion,COUNT(*) FROM observations GROUP BY promotion").fetchall())
        return {"counts": counts, "generated_at": int(time.time()), "min_repeat": self.min_repeat}


__all__ = ["DreamMemory"]
