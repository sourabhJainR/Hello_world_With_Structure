"""Public facade for durable AER scheduling.

Compatibility methods here adapt the earlier receipt-oriented API to the
unified claim-before-run scheduler without duplicating scheduler state.
"""
from datetime import datetime
from pathlib import Path
import sqlite3

from .agent_capabilities import AutomationScheduler as _AutomationScheduler, Schedule


class AutomationScheduler(_AutomationScheduler):
    def finish(self, schedule_or_claim: str, claim_or_status: str, status_or_detail: str = "", detail: str = "", *, now: datetime | None = None) -> None:
        # New API: finish(schedule_id, claim, status, detail=...).
        if claim_or_status in {"success", "retryable", "failed", "cancelled"}:
            claim = schedule_or_claim
            status = claim_or_status
            resolved_detail = status_or_detail
            with sqlite3.connect(self.path) as db:
                row = db.execute("SELECT schedule_id FROM runs WHERE id=?", (claim,)).fetchone()
                if row:
                    return super().finish(row[0], claim, status, resolved_detail or detail, now=now)
                row = db.execute("SELECT id FROM schedules WHERE claim=?", (claim,)).fetchone()
            if not row:
                raise KeyError("invalid scheduler claim")
            return super().finish(row[0], claim, status, resolved_detail or detail, now=now)
        return super().finish(schedule_or_claim, claim_or_status, status_or_detail, detail, now=now)

    def find_task(self, task: str) -> Schedule | None:
        """Return the existing durable schedule for an exact task, if any."""
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT id,task,interval_seconds,max_attempts,next_run,enabled,attempts "
                "FROM schedules WHERE task=? ORDER BY id LIMIT 1",
                (task,),
            ).fetchone()
        if row is None:
            return None
        return Schedule(row[0], row[1], int(row[2]), int(row[3]), row[4], bool(row[5]), int(row[6]))

    def recent_runs(self, schedule_id: str, limit: int = 20) -> list[dict[str, str | None]]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT id,schedule_id,started_at,finished_at,status,detail FROM runs WHERE schedule_id=? ORDER BY finished_at DESC LIMIT ?",
                (schedule_id, limit),
            ).fetchall()
        return [dict(id=r[0], schedule_id=r[1], started_at=r[2], finished_at=r[3], status=r[4], detail=r[5]) for r in rows]

    def close(self) -> None:
        return None


__all__ = ["AutomationScheduler", "Schedule"]
