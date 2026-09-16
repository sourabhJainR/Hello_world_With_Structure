"""Durable mission and goal state for long-horizon AER work.

Goals persist independently from a single orchestration run. They provide
structure for long-horizon work while leaving execution, permissions and
verification with the existing AER control plane.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Any

from .persistent_memory import PersistentMemory

_STATUSES = frozenset({"open", "active", "blocked", "completed", "abandoned"})


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class Goal:
    goal_id: str
    title: str
    description: str = ""
    parent_id: str | None = None
    priority: int = 50
    status: str = "open"
    created_at: str = ""

    def __post_init__(self) -> None:
        for name, value in (("goal_id", self.goal_id), ("title", self.title)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.parent_id == self.goal_id:
            raise ValueError("goal cannot be its own parent")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")
        if self.status not in _STATUSES:
            raise ValueError("invalid goal status")
        if not self.created_at:
            object.__setattr__(self, "created_at", _utc())
        object.__setattr__(self, "created_at", _timestamp(self.created_at))


class GoalManager:
    """Persist goals with bounded hierarchy and explicit state transitions."""

    def __init__(self, memory: PersistentMemory, project: str, *, max_goals: int = 20_000) -> None:
        if not isinstance(memory, PersistentMemory):
            raise TypeError("memory must be a PersistentMemory instance")
        if not isinstance(project, str) or not project.strip():
            raise ValueError("project is required")
        if max_goals < 1:
            raise ValueError("max_goals must be positive")
        self.memory = memory
        self.project = project
        self.max_goals = max_goals
        with sqlite3.connect(memory.path, timeout=10) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS goals(
                project TEXT NOT NULL, goal_id TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT NOT NULL, parent_id TEXT, priority INTEGER NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(project, goal_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_goals_parent ON goals(project, parent_id, priority, goal_id)")

    def create(self, goal: Goal) -> Goal:
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            if goal.parent_id and not db.execute("SELECT 1 FROM goals WHERE project=? AND goal_id=?", (self.project, goal.parent_id)).fetchone():
                raise KeyError("parent goal does not exist")
            existing = db.execute("SELECT title,description,parent_id,priority,status,created_at FROM goals WHERE project=? AND goal_id=?", (self.project, goal.goal_id)).fetchone()
            expected = (goal.title, goal.description, goal.parent_id, goal.priority, goal.status, goal.created_at)
            if existing:
                if existing != expected:
                    raise ValueError("goal_id already exists with different content")
                return goal
            count = db.execute("SELECT COUNT(*) FROM goals WHERE project=?", (self.project,)).fetchone()[0]
            if count >= self.max_goals:
                raise ValueError("goal budget exceeded")
            db.execute("INSERT INTO goals VALUES(?,?,?,?,?,?,?,?)", (self.project, goal.goal_id, goal.title, goal.description,
                       goal.parent_id, goal.priority, goal.status, goal.created_at))
        return goal

    def get(self, goal_id: str) -> Goal | None:
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            row = db.execute("SELECT goal_id,title,description,parent_id,priority,status,created_at FROM goals WHERE project=? AND goal_id=?", (self.project, goal_id)).fetchone()
        return Goal(*row) if row else None

    def children(self, parent_id: str | None = None, *, limit: int = 100) -> tuple[Goal, ...]:
        if limit < 1:
            return ()
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            if parent_id is None:
                rows = db.execute("SELECT goal_id,title,description,parent_id,priority,status,created_at FROM goals WHERE project=? AND parent_id IS NULL ORDER BY priority DESC,goal_id LIMIT ?", (self.project, limit)).fetchall()
            else:
                rows = db.execute("SELECT goal_id,title,description,parent_id,priority,status,created_at FROM goals WHERE project=? AND parent_id=? ORDER BY priority DESC,goal_id LIMIT ?", (self.project, parent_id, limit)).fetchall()
        return tuple(Goal(*row) for row in rows)

    def set_status(self, goal_id: str, status: str) -> Goal:
        if status not in _STATUSES:
            raise ValueError("invalid goal status")
        goal = self.get(goal_id)
        if goal is None:
            raise KeyError("goal does not exist")
        if goal.status in {"completed", "abandoned"} and status != goal.status:
            raise ValueError("terminal goal cannot be reopened")
        updated = Goal(goal.goal_id, goal.title, goal.description, goal.parent_id, goal.priority, status, goal.created_at)
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            db.execute("UPDATE goals SET status=? WHERE project=? AND goal_id=?", (status, self.project, goal_id))
        return updated

    def ready(self, *, limit: int = 100) -> tuple[Goal, ...]:
        if limit < 1:
            return ()
        with sqlite3.connect(self.memory.path, timeout=10) as db:
            rows = db.execute("SELECT goal_id,title,description,parent_id,priority,status,created_at FROM goals WHERE project=? AND status IN ('open','active') ORDER BY priority DESC,goal_id LIMIT ?", (self.project, limit)).fetchall()
        return tuple(Goal(*row) for row in rows)


__all__ = ["Goal", "GoalManager"]
