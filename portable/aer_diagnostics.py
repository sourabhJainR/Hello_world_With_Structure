"""Read-only AER end-user diagnostics and control-center views.

This module is intentionally a consumer of existing AER state owners. It never
creates or mutates AER state; it only reads installation metadata, SQLite
inventories, session checkpoints, trigger records, and adaptive-policy state.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .session_state import SessionStore

_PROVIDER_COMMANDS = ("claude", "codex", "gemini")
_SKILL_DESTINATIONS = {
    "agents": Path.home() / ".agents" / "skills" / "ai-coding-orchestrator",
    "claude": Path.home() / ".claude" / "skills" / "ai-coding-orchestrator",
    "gemini": Path.home() / ".gemini" / "skills" / "ai-coding-orchestrator",
}


def _aer_home(value: Path | str | None) -> Path:
    return Path(value or (Path.home() / ".aer")).expanduser().resolve()


def _project_root(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    return Path(value).expanduser().resolve()


def _generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _installation(aer_home: Path) -> dict[str, Any]:
    active_path = aer_home / "active.json"
    current = aer_home / "current"
    if not active_path.is_file() or not (current.exists() or current.is_symlink()):
        return {
            "active": False,
            "status": "unconfigured",
            "version": None,
            "source_commit": None,
            "bundle_sha256": None,
            "install_root": None,
        }

    active = _read_json(active_path)
    if active is None:
        return {"active": False, "status": "error", "error": "active.json is unreadable"}

    install_json = current / "install.json"
    installed = _read_json(install_json) if install_json.is_file() else None
    status = "ok"
    error = None
    if installed is None:
        status = "error"
        error = "active installation is missing or has invalid install.json"
    else:
        for key in ("version", "source_commit", "bundle_sha256", "install_root"):
            if active.get(key) != installed.get(key):
                status = "error"
                error = f"active.json and install.json disagree on {key}"
                break
        if status == "ok" and str(active.get("install_root", "")) != current.name:
            status = "error"
            error = "current installation pointer does not match active install_root"

    result: dict[str, Any] = {
        "active": status == "ok",
        "status": status,
        "version": active.get("version"),
        "source_commit": active.get("source_commit"),
        "bundle_sha256": active.get("bundle_sha256"),
        "install_root": active.get("install_root"),
        "current_path": str(current),
    }
    if error:
        result["error"] = error
    return result


def _providers() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for name in _PROVIDER_COMMANDS:
        path = shutil.which(name)
        items.append({
            "name": f"provider:{name}",
            "status": "ok" if path else "warning",
            "detail": f"available at {path}" if path else "CLI not found; integration remains optional",
        })
    return items


def _skill_checks(aer_home: Path) -> list[dict[str, str]]:
    current = aer_home / "current" / "skills" / "ai-coding-orchestrator" / "SKILL.md"
    if not current.is_file():
        return []
    canonical_hash = _safe_sha256(current)
    if not canonical_hash:
        return []
    checks: list[dict[str, str]] = []
    for name, destination in _SKILL_DESTINATIONS.items():
        path = destination / "SKILL.md"
        if not path.is_file():
            checks.append({
                "name": f"skill:{name}",
                "status": "warning",
                "detail": f"not installed at {path}",
            })
            continue
        installed_hash = _safe_sha256(path)
        if installed_hash == canonical_hash:
            checks.append({
                "name": f"skill:{name}",
                "status": "ok",
                "detail": f"in sync at {path}",
            })
        else:
            checks.append({
                "name": f"skill:{name}",
                "status": "error",
                "detail": f"installed skill differs from active AER at {path}",
            })
    return checks


def _db_integrity(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {"status": "warning", "detail": "state database not created yet"}
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5) as db:
            result = db.execute("PRAGMA integrity_check").fetchone()
        detail = str(result[0] if result else "no result")
        return {"status": "ok" if detail == "ok" else "error", "detail": detail}
    except sqlite3.Error as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}


def _table_exists(path: Path, table: str) -> bool:
    if not path.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5) as db:
            return bool(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
            ).fetchone())
    except sqlite3.Error:
        return False


def _trigger_summary(aer_home: Path) -> dict[str, Any]:
    path = aer_home / "automation" / "automation.db"
    if not path.is_file() or not _table_exists(path, "trigger_events"):
        return {"configured": False, "counts": {}, "recent": []}
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5) as db:
            rows = db.execute(
                "SELECT status,COUNT(*) FROM trigger_events GROUP BY status ORDER BY status"
            ).fetchall()
            recent = db.execute(
                "SELECT event_id,kind,status,attempts,max_attempts,created_at,completed_at,last_detail "
                "FROM trigger_events ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        return {
            "configured": True,
            "counts": {str(row[0]): int(row[1]) for row in rows},
            "recent": [
                {
                    "id": row[0],
                    "kind": row[1],
                    "status": row[2],
                    "attempts": int(row[3]),
                    "max_attempts": int(row[4]),
                    "created_at": row[5],
                    "completed_at": row[6],
                    "last_detail": row[7],
                }
                for row in recent
            ],
        }
    except sqlite3.Error as exc:
        return {"configured": True, "error": f"{type(exc).__name__}: {exc}", "counts": {}, "recent": []}


def _sessions(aer_home: Path, project_root: Path | None) -> list[dict[str, Any]]:
    store = SessionStore(aer_home / "sessions")
    if not store.root.is_dir():
        return []
    project_key = store.project_key(project_root) if project_root else None
    sessions: list[dict[str, Any]] = []
    for path in sorted(store.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        checkpoint = store.load(path.stem)
        if checkpoint is None:
            continue
        if project_key and checkpoint.project_key != project_key:
            continue
        item = {
            "session_id": checkpoint.session_id,
            "task_id": checkpoint.task_id,
            "project_key": checkpoint.project_key,
            "project_root": checkpoint.project_root,
            "intent": checkpoint.intent,
            "stage": checkpoint.stage,
            "completed_batches": list(checkpoint.completed_batches),
            "remaining_batches": list(checkpoint.remaining_batches),
            "active_provider": checkpoint.active_provider,
            "attempt": checkpoint.attempt,
            "last_error": checkpoint.last_error,
            "updated_at": checkpoint.updated_at,
            "recoverable": True,
        }
        if checkpoint.project_root or checkpoint.intent:
            item["resume_hint"] = "reopen the repository with this session context; AER will not execute it automatically"
        sessions.append(item)
        if len(sessions) >= 20:
            break
    return sessions


def _learning(aer_home: Path, project_root: Path | None) -> dict[str, Any]:
    memory_path = aer_home / "memory" / "memory.db"
    if not memory_path.is_file() or not _table_exists(memory_path, "adaptive_policies"):
        return {"configured": False, "policy": None, "maintenance": [], "experience_count": 0}

    project = SessionStore.project_key(project_root) if project_root else "global"
    try:
        with sqlite3.connect(f"file:{memory_path.as_posix()}?mode=ro", uri=True, timeout=5) as db:
            row = db.execute(
                "SELECT version,parent_version,strategy,confidence_adjustment,iteration_target,created_at,status,evidence_digest "
                "FROM adaptive_policies WHERE project=? AND scope='global' AND status='active' "
                "ORDER BY created_at DESC,version DESC LIMIT 1",
                (project,),
            ).fetchone()
            experience_row = db.execute(
                "SELECT COUNT(*) FROM adaptive_experience_history WHERE project=?", (project,)
            ).fetchone()
            receipts = db.execute(
                "SELECT cycle_id,started_at,finished_at,jobs_processed,strategy_action,policy_version,errors,digest "
                "FROM adaptive_maintenance_receipts WHERE project=? ORDER BY finished_at DESC LIMIT 10",
                (project,),
            ).fetchall()
    except sqlite3.Error as exc:
        return {"configured": True, "error": f"{type(exc).__name__}: {exc}", "policy": None, "maintenance": [], "experience_count": 0}

    policy = None
    if row:
        policy = {
            "version": row[0],
            "parent_version": row[1],
            "strategy": row[2],
            "confidence_adjustment": float(row[3]),
            "iteration_target": float(row[4]),
            "created_at": row[5],
            "status": row[6],
            "evidence_digest": row[7],
        }
    return {
        "configured": True,
        "project_key": project,
        "policy": policy,
        "experience_count": int(experience_row[0] if experience_row else 0),
        "maintenance": [
            {
                "cycle_id": item[0],
                "started_at": item[1],
                "finished_at": item[2],
                "jobs_processed": int(item[3]),
                "strategy_action": item[4],
                "policy_version": item[5],
                "errors": json.loads(item[6]) if item[6] else [],
                "digest": item[7],
            }
            for item in receipts
        ],
    }


def collect_status(
    aer_home: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    home = _aer_home(aer_home)
    project = _project_root(project_root)
    installation = _installation(home)
    triggers = _trigger_summary(home)
    sessions = _sessions(home, project)
    learning = _learning(home, project)
    latest_report = None
    if project:
        path = project / ".ai-harness" / "reports" / "latest.html"
        if path.is_file():
            latest_report = {"path": str(path), "size": path.stat().st_size, "modified_at": path.stat().st_mtime}

    overall = installation["status"]
    if overall == "ok" and any(item["status"] == "error" for item in _skill_checks(home)):
        overall = "error"
    if overall == "ok" and any(item["status"] == "warning" for item in _providers()):
        overall = "warning"

    return {
        "command": "status",
        "status": overall,
        "generated_at": _generated_at(),
        "aer_home": str(home),
        "installation": installation,
        "providers": _providers(),
        "triggers": triggers,
        "sessions": {"count": len(sessions), "recent": sessions[:5]},
        "learning": {
            "configured": learning.get("configured", False),
            "experience_count": learning.get("experience_count", 0),
            "policy": learning.get("policy"),
            "last_maintenance": learning.get("maintenance", [None])[0] if learning.get("maintenance") else None,
        },
        "latest_report": latest_report,
    }


def run_doctor(
    aer_home: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    home = _aer_home(aer_home)
    project = _project_root(project_root)
    items: list[dict[str, str]] = []

    installation = _installation(home)
    if installation["status"] == "ok":
        items.append({"name": "active_installation", "status": "ok", "detail": f"AER {installation['version']} is active"})
    elif installation["status"] == "unconfigured":
        items.append({"name": "active_installation", "status": "error", "detail": "AER is not installed; install a verified portable bundle first"})
    else:
        items.append({"name": "active_installation", "status": "error", "detail": str(installation.get("error", "active installation is invalid"))})

    for label, path in (
        ("automation_database", home / "automation" / "automation.db"),
        ("memory_database", home / "memory" / "memory.db"),
    ):
        result = _db_integrity(path)
        items.append({"name": label, **result})

    if (home / "sessions").is_dir():
        valid = len(_sessions(home, project))
        items.append({"name": "session_store", "status": "ok", "detail": f"{valid} recoverable session(s) visible"})
    else:
        items.append({"name": "session_store", "status": "warning", "detail": "no session store has been created yet"})

    items.extend(_providers())
    skill_items = _skill_checks(home)
    if skill_items:
        items.extend(skill_items)

    if project:
        items.append({
            "name": "project_root",
            "status": "ok" if project.is_dir() else "error",
            "detail": f"project root: {project}" if project.is_dir() else f"project root does not exist: {project}",
        })
        report = project / ".ai-harness" / "reports" / "latest.html"
        items.append({
            "name": "latest_report",
            "status": "ok" if report.is_file() else "warning",
            "detail": str(report) if report.is_file() else "no engineering report found for this project",
        })

    errors = [item for item in items if item["status"] == "error"]
    warnings = [item for item in items if item["status"] == "warning"]
    status = "error" if errors else "warning" if warnings else "ok"
    return {
        "command": "doctor",
        "status": status,
        "generated_at": _generated_at(),
        "aer_home": str(home),
        "items": items,
        "next": (
            "Install or repair the active AER installation." if any(item["name"] == "active_installation" and item["status"] == "error" for item in items)
            else "Optional provider integrations are missing; install the provider CLI you intend to use."
            if warnings else
            "AER local control-plane checks are healthy."
        ),
    }


def list_sessions(
    aer_home: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    home = _aer_home(aer_home)
    project = _project_root(project_root)
    sessions = _sessions(home, project)
    return {
        "command": "sessions",
        "status": "ok",
        "generated_at": _generated_at(),
        "aer_home": str(home),
        "count": len(sessions),
        "sessions": sessions,
    }


def trigger_status(
    trigger_id: str,
    aer_home: Path | str | None = None,
) -> dict[str, Any]:
    clean_id = trigger_id.strip()
    if not clean_id:
        raise ValueError("trigger_id is required")
    home = _aer_home(aer_home)
    path = home / "automation" / "automation.db"
    if not path.is_file() or not _table_exists(path, "trigger_events"):
        return {
            "command": "trigger-status",
            "status": "not_found",
            "generated_at": _generated_at(),
            "trigger": None,
        }
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5) as db:
            row = db.execute(
                "SELECT event_id,kind,status,attempts,max_attempts,priority,available_at,claimed_at,lease_until,completed_at,last_detail,outcome "
                "FROM trigger_events WHERE event_id=?",
                (clean_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        return {
            "command": "trigger-status",
            "status": "error",
            "generated_at": _generated_at(),
            "trigger": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if row is None:
        return {
            "command": "trigger-status",
            "status": "not_found",
            "generated_at": _generated_at(),
            "trigger": None,
        }
    try:
        outcome = json.loads(row[11] or "{}")
    except (TypeError, json.JSONDecodeError):
        outcome = {"invalid_persisted_outcome": True}
    return {
        "command": "trigger-status",
        "status": str(row[2]),
        "generated_at": _generated_at(),
        "trigger": {
            "id": row[0],
            "kind": row[1],
            "status": row[2],
            "attempts": int(row[3]),
            "max_attempts": int(row[4]),
            "priority": int(row[5]),
            "available_at": row[6],
            "claimed_at": row[7],
            "lease_until": row[8],
            "completed_at": row[9],
            "last_detail": row[10],
            "outcome": outcome,
        },
    }


def learning_status(
    aer_home: Path | str | None = None,
    project_root: Path | str | None = None,
) -> dict[str, Any]:
    home = _aer_home(aer_home)
    project = _project_root(project_root)
    value = _learning(home, project)
    value.update({
        "command": "learning",
        "status": "ok" if "error" not in value else "error",
        "generated_at": _generated_at(),
        "aer_home": str(home),
    })
    return value


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(dict(report), indent=2, sort_keys=True, default=str)


def render_text(report: Mapping[str, Any]) -> str:
    command = str(report.get("command", "status"))
    status = str(report.get("status", "unknown"))
    lines = [f"AER {command}: {status}"]

    if command == "status":
        installation = report.get("installation") or {}
        lines.append(f"Version: {installation.get('version') or 'not installed'}")
        lines.append(f"Source: {str(installation.get('source_commit') or 'n/a')[:12]}")
        providers = report.get("providers") or []
        lines.append("Providers: " + ", ".join(
            f"{str(item.get('name', '')).removeprefix('provider:')}={item.get('status')}"
            for item in providers
        ))
        triggers = report.get("triggers") or {}
        counts = triggers.get("counts") or {}
        lines.append("Triggers: " + (", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"))
        sessions = report.get("sessions") or {}
        lines.append(f"Sessions: {sessions.get('count', 0)}")
        learning = report.get("learning") or {}
        policy = learning.get("policy")
        lines.append(f"Learning: {'active ' + str(policy.get('version')) if policy else 'not initialized'}")
        latest = report.get("latest_report")
        if latest:
            lines.append(f"Latest report: {latest.get('path')}")
        return "\n".join(lines)

    if command == "doctor":
        for item in report.get("items", []):
            lines.append(f"[{item.get('status', 'unknown').upper()}] {item.get('name')}: {item.get('detail')}")
        if report.get("next"):
            lines.append(f"Next: {report['next']}")
        return "\n".join(lines)

    if command == "sessions":
        for item in report.get("sessions", []):
            lines.append(
                f"{item['session_id']} stage={item['stage']} provider={item.get('active_provider') or 'n/a'} "
                f"attempt={item['attempt']} task={item['task_id']}"
            )
            if item.get("resume_hint"):
                lines.append(f"  Resume: {item['resume_hint']}")
        return "\n".join(lines)

    if command == "trigger-status":
        trigger = report.get("trigger")
        if not trigger:
            lines.append("Trigger not found.")
        else:
            lines.extend([
                f"ID: {trigger['id']}",
                f"Kind: {trigger['kind']}",
                f"Attempts: {trigger['attempts']}/{trigger['max_attempts']}",
                f"Priority: {trigger['priority']}",
                f"Available: {trigger['available_at']}",
                f"Completed: {trigger.get('completed_at') or 'pending'}",
                f"Detail: {trigger.get('last_detail') or 'n/a'}",
            ])
        return "\n".join(lines)

    if command == "learning":
        policy = report.get("policy")
        if policy:
            lines.extend([
                f"Project: {report.get('project_key')}",
                f"Policy: {policy['version']} strategy={policy['strategy']}",
                f"Confidence adjustment: {policy['confidence_adjustment']}",
                f"Iteration target: {policy['iteration_target']}",
                f"Experience records: {report.get('experience_count', 0)}",
            ])
        else:
            lines.append("Learning policy is not initialized for this project.")
        return "\n".join(lines)

    return "\n".join(lines)


__all__ = [
    "collect_status",
    "run_doctor",
    "list_sessions",
    "trigger_status",
    "learning_status",
    "render_json",
    "render_text",
]
