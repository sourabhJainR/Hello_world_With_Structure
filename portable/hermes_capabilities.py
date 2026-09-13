"""Unified agent capability layer inspired by Hermes Agent, implemented for AER.

The source project demonstrates a strong set of operational capabilities: durable
memory, session recall, progressive-disclosure skills, explicit toolsets,
background processes, delegation, scheduling, provider/model fallback, multiple
execution backends and verification-aware UX.  This module folds those ideas
into AER's existing contracts instead of introducing a parallel agent runtime.

Design rules:
- AER owns semantics, safety, evidence, verification and promotion.
- Capabilities are adapters behind one registry and one runtime facade.
- Durable state is scoped by project/session/intent where applicable.
- Unsupported external backends are represented as unavailable, never faked.
- All writes that affect future behavior are auditable and gateable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .task_planner import Task, TaskPlan


CAPABILITY_NAMES = (
    "web",
    "search",
    "terminal",
    "file",
    "browser",
    "vision",
    "image_gen",
    "skills",
    "tts",
    "todo",
    "memory",
    "session_search",
    "cronjob",
    "code_execution",
    "delegation",
    "clarify",
    "mcp",
)

TOOLSET_PRESETS = {
    "safe": ("file", "search", "memory", "session_search", "todo"),
    "coding": ("terminal", "file", "search", "skills", "memory", "session_search", "delegation"),
    "research": ("web", "search", "file", "browser", "memory", "session_search", "delegation"),
    "automation": ("terminal", "file", "cronjob", "memory", "session_search"),
    "full": CAPABILITY_NAMES,
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*['\"]?[^\s,;'\"]+"),
    re.compile(r"-----BEGIN [A-Z0-9 ]+ PRIVATE KEY-----"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{16,}\b"),
)
_INJECTION_PATTERNS = (
    re.compile(r"(?i)ignore\s+(all|previous|prior)\s+instructions"),
    re.compile(r"(?i)system\s+prompt"),
    re.compile(r"(?i)exfiltrat|steal\s+(the\s+)?credentials"),
    re.compile(r"(?i)curl\s+[^\n]+\$\{?[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD)"),
)


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    builtin: bool = False
    requires: tuple[str, ...] = ()
    fallback: str | None = None
    risk: str = "low"


@dataclass(frozen=True)
class CapabilityState:
    name: str
    status: str
    provider: str
    reason: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryEntry:
    entry_id: str
    target: str
    content: str
    created_at: float
    updated_at: float
    source: str
    intent_digest: str | None = None


@dataclass(frozen=True)
class MemoryMutation:
    mutation_id: str
    action: str
    target: str
    content: str | None
    old_text: str | None
    created_at: float
    source: str
    approved: bool = False


@dataclass(frozen=True)
class SessionMessage:
    session_id: str
    seq: int
    role: str
    content: str
    created_at: float


@dataclass(frozen=True)
class ProcessReceipt:
    session_id: str
    command: tuple[str, ...]
    started_at: float
    finished_at: float | None
    exit_code: int | None
    output_tail: str
    status: str


@dataclass(frozen=True)
class DelegationReceipt:
    task_id: str
    status: str
    started_at: float
    finished_at: float
    attempts: int
    output: Any = None
    error: str | None = None


@dataclass(frozen=True)
class CronJob:
    job_id: str
    name: str
    schedule: str
    task_id: str
    enabled: bool
    next_run_at: float | None
    last_run_at: float | None = None
    last_status: str | None = None


@dataclass(frozen=True)
class QualityFinding:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class QualityReport:
    accepted: bool
    findings: tuple[QualityFinding, ...]


class CapabilityRegistry:
    """Single capability registry for provider discovery and AER fallbacks."""

    SPECS = {
        "web": CapabilitySpec("web", "web retrieval and extraction", fallback="search"),
        "search": CapabilitySpec("search", "local or remote evidence search", builtin=True),
        "terminal": CapabilitySpec("terminal", "command execution through a configured backend", builtin=True, risk="medium"),
        "file": CapabilitySpec("file", "safe file inspection and mutation", builtin=True, risk="medium"),
        "browser": CapabilitySpec("browser", "interactive browser automation", risk="medium"),
        "vision": CapabilitySpec("vision", "image understanding", risk="low"),
        "image_gen": CapabilitySpec("image_gen", "image generation", risk="medium"),
        "skills": CapabilitySpec("skills", "procedural knowledge registry", builtin=True),
        "tts": CapabilitySpec("tts", "text to speech", risk="low"),
        "todo": CapabilitySpec("todo", "durable dependency-aware task planning", builtin=True),
        "memory": CapabilitySpec("memory", "curated persistent memory", builtin=True),
        "session_search": CapabilitySpec("session_search", "FTS-backed conversation recall", builtin=True),
        "cronjob": CapabilitySpec("cronjob", "durable scheduled execution", builtin=True, risk="medium"),
        "code_execution": CapabilitySpec("code_execution", "bounded programmatic tool execution", builtin=True, risk="high"),
        "delegation": CapabilitySpec("delegation", "parallel isolated task delegation", builtin=True, risk="medium"),
        "clarify": CapabilitySpec("clarify", "structured user clarification", builtin=True),
        "mcp": CapabilitySpec("mcp", "external tool interoperability", risk="high"),
    }

    def __init__(self) -> None:
        self._states: dict[str, CapabilityState] = {}

    def register(self, name: str, status: str, *, provider: str = "aer", reason: str = "", evidence: Iterable[str] = ()) -> None:
        if name not in self.SPECS:
            raise ValueError(f"unknown capability: {name}")
        if status not in {"native", "fallback", "unavailable"}:
            raise ValueError(f"invalid capability state: {status}")
        self._states[name] = CapabilityState(name, status, provider, reason, tuple(sorted(set(evidence))))

    def discover(self, explicit: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, CapabilityState]:
        explicit = explicit or {}
        for name, spec in self.SPECS.items():
            item = explicit.get(name)
            if item:
                self.register(name, str(item.get("status", "unavailable")), provider=str(item.get("provider", "aer")), reason=str(item.get("reason", "")), evidence=item.get("evidence", []))
            elif spec.builtin:
                self.register(name, "fallback", provider="aer", reason="AER provides the canonical implementation")
            else:
                self.register(name, "unavailable", provider="aer", reason="no verified adapter is configured")
        return dict(self._states)

    def require(self, name: str) -> CapabilityState:
        if name not in self._states:
            self.discover()
        state = self._states[name]
        if state.status == "unavailable":
            raise RuntimeError(f"capability unavailable: {name}; {state.reason}")
        return state

    def toolset(self, name: str) -> tuple[str, ...]:
        try:
            return tuple(TOOLSET_PRESETS[name])
        except KeyError as exc:
            raise ValueError(f"unknown toolset: {name}") from exc

    def export(self) -> dict[str, Any]:
        return {name: asdict(state) for name, state in sorted(self._states.items())}


class MemoryStore:
    """Bounded memory + exact session recall with staged writes and dedupe."""

    def __init__(self, root: Path | str | None = None, *, memory_limit: int = 2200, user_limit: int = 1375) -> None:
        self.root = Path(root or (Path.home() / ".aer" / "memory")).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "state.db"
        self.memory_limit = memory_limit
        self.user_limit = user_limit
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memory(
                    entry_id TEXT PRIMARY KEY, target TEXT NOT NULL, content TEXT NOT NULL,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL, source TEXT NOT NULL,
                    intent_digest TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_memory_content ON memory(target, content);
                CREATE TABLE IF NOT EXISTS pending_mutations(
                    mutation_id TEXT PRIMARY KEY, action TEXT NOT NULL, target TEXT NOT NULL,
                    content TEXT, old_text TEXT, created_at REAL NOT NULL, source TEXT NOT NULL,
                    approved INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS session_messages(
                    session_id TEXT NOT NULL, seq INTEGER NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, created_at REAL NOT NULL,
                    PRIMARY KEY(session_id, seq)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS session_fts USING fts5(
                    session_id UNINDEXED, seq UNINDEXED, role, content
                );
                """
            )

    @staticmethod
    def _scan(text: str) -> None:
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
            raise ValueError("memory content resembles a secret or credential")
        if any(pattern.search(text) for pattern in _INJECTION_PATTERNS):
            raise ValueError("memory content resembles prompt injection or credential exfiltration")
        if any(ord(ch) in {0x202A, 0x202B, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069} for ch in text):
            raise ValueError("memory content contains bidi control characters")

    def _limit_for(self, target: str) -> int:
        if target not in {"memory", "user"}:
            raise ValueError("target must be 'memory' or 'user'")
        return self.memory_limit if target == "memory" else self.user_limit

    def list(self, target: str) -> list[MemoryEntry]:
        self._limit_for(target)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM memory WHERE target=? ORDER BY updated_at DESC", (target,)).fetchall()
        return [MemoryEntry(**dict(row)) for row in rows]

    def add(self, target: str, content: str, *, source: str = "agent", intent_digest: str | None = None, approval_required: bool = False) -> MemoryEntry | MemoryMutation:
        self._scan(content)
        limit = self._limit_for(target)
        with self._lock:
            current = sum(len(item.content) for item in self.list(target))
            if any(item.content == content for item in self.list(target)):
                return self.list(target)[0] if self.list(target) else self._entry(target, content, source, intent_digest)
            if current + len(content) > limit:
                raise ValueError(f"{target} memory capacity exceeded: {current}/{limit}; consolidate before adding")
            if approval_required:
                return self._stage("add", target, content, None, source)
            return self._insert(target, content, source, intent_digest)

    def replace(self, target: str, old_text: str, content: str, *, source: str = "agent", approval_required: bool = False) -> MemoryEntry | MemoryMutation:
        self._scan(content)
        matches = [item for item in self.list(target) if old_text in item.content]
        if len(matches) != 1:
            raise ValueError(f"replace requires exactly one matching entry; found {len(matches)}")
        if approval_required:
            return self._stage("replace", target, content, old_text, source)
        self.remove(target, old_text, source=source)
        return self._insert(target, content, source, matches[0].intent_digest)

    def remove(self, target: str, old_text: str, *, source: str = "agent", approval_required: bool = False) -> MemoryMutation | bool:
        matches = [item for item in self.list(target) if old_text in item.content]
        if len(matches) != 1:
            raise ValueError(f"remove requires exactly one matching entry; found {len(matches)}")
        if approval_required:
            return self._stage("remove", target, None, old_text, source)
        with self._connect() as conn:
            conn.execute("DELETE FROM memory WHERE entry_id=?", (matches[0].entry_id,))
            conn.commit()
        return True

    def pending(self) -> list[MemoryMutation]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pending_mutations WHERE approved=0 ORDER BY created_at").fetchall()
        return [MemoryMutation(**{**dict(row), "approved": bool(row["approved"])}) for row in rows]

    def approve(self, mutation_id: str) -> MemoryEntry | bool:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM pending_mutations WHERE mutation_id=?", (mutation_id,)).fetchone()
        if not row:
            raise KeyError(mutation_id)
        action = row["action"]
        if action == "add":
            result = self.add(row["target"], row["content"], source=row["source"], approval_required=False)
        elif action == "replace":
            result = self.replace(row["target"], row["old_text"], row["content"], source=row["source"], approval_required=False)
        elif action == "remove":
            result = self.remove(row["target"], row["old_text"], source=row["source"], approval_required=False)
        else:
            raise ValueError(action)
        with self._connect() as conn:
            conn.execute("DELETE FROM pending_mutations WHERE mutation_id=?", (mutation_id,))
            conn.commit()
        return result

    def reject(self, mutation_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pending_mutations WHERE mutation_id=?", (mutation_id,))
            conn.commit()

    def index_session(self, session_id: str, messages: Sequence[tuple[str, str]]) -> None:
        with self._connect() as conn:
            for seq, (role, content) in enumerate(messages, start=1):
                if conn.execute("SELECT 1 FROM session_messages WHERE session_id=? AND seq=?", (session_id, seq)).fetchone():
                    continue
                created_at = time.time()
                conn.execute("INSERT INTO session_messages VALUES(?,?,?,?,?)", (session_id, seq, role, content, created_at))
                conn.execute("INSERT INTO session_fts VALUES(?,?,?,?)", (session_id, seq, role, content))
            conn.commit()

    def search_session(self, query: str, *, limit: int = 20) -> list[SessionMessage]:
        if not query.strip():
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id, seq, role, content, rowid FROM session_fts WHERE session_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
            result = []
            for row in rows:
                base = conn.execute("SELECT created_at FROM session_messages WHERE session_id=? AND seq=?", (row["session_id"], row["seq"])).fetchone()
                result.append(SessionMessage(row["session_id"], row["seq"], row["role"], row["content"], float(base["created_at"])))
            return result

    def _stage(self, action: str, target: str, content: str | None, old_text: str | None, source: str) -> MemoryMutation:
        mutation_id = hashlib.sha256(f"{action}|{target}|{content}|{old_text}|{time.time_ns()}".encode()).hexdigest()[:16]
        mutation = MemoryMutation(mutation_id, action, target, content, old_text, time.time(), source, False)
        with self._connect() as conn:
            conn.execute("INSERT INTO pending_mutations VALUES(?,?,?,?,?,?,?,0)", (mutation.mutation_id, mutation.action, mutation.target, mutation.content, mutation.old_text, mutation.created_at, mutation.source))
            conn.commit()
        return mutation

    def _entry(self, target: str, content: str, source: str, intent_digest: str | None) -> MemoryEntry:
        now = time.time()
        return MemoryEntry(hashlib.sha256(f"{target}|{content}".encode()).hexdigest()[:16], target, content, now, now, source, intent_digest)

    def _insert(self, target: str, content: str, source: str, intent_digest: str | None) -> MemoryEntry:
        entry = self._entry(target, content, source, intent_digest)
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO memory VALUES(?,?,?,?,?,?,?)", asdict(entry).values())
            conn.commit()
        return entry


class SkillRegistry:
    """Progressive-disclosure skill registry with conditional activation and audit."""

    def __init__(self, roots: Sequence[Path | str]) -> None:
        self.roots = [Path(root).expanduser() for root in roots]

    def scan(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for root in self.roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("SKILL.md")):
                try:
                    text = path.read_text(encoding="utf-8")
                    meta, body = self._parse(text)
                    self._security_scan(text)
                except (OSError, UnicodeDecodeError, ValueError) as exc:
                    results.append({"path": str(path), "status": "invalid", "error": str(exc)})
                    continue
                results.append({"path": str(path), "status": "ready", "metadata": meta, "description": meta.get("description", ""), "body_chars": len(body)})
        return results

    def list(self, *, available_tools: Iterable[str] = (), platform: str | None = None) -> list[dict[str, Any]]:
        tools = set(available_tools)
        items = []
        for item in self.scan():
            if item.get("status") != "ready":
                continue
            meta = item["metadata"]
            if platform and platform not in set(meta.get("platforms", []) or []) and meta.get("platforms"):
                continue
            hermes = meta.get("metadata", {}).get("aer", meta.get("metadata", {}).get("hermes", {}))
            required = set(hermes.get("requires_tools", []) or []) | set(hermes.get("requires_toolsets", []) or [])
            fallbacks = set(hermes.get("fallback_for_tools", []) or []) | set(hermes.get("fallback_for_toolsets", []) or [])
            if required and not required.issubset(tools):
                continue
            if fallbacks and fallbacks.intersection(tools):
                continue
            items.append({"name": meta.get("name", Path(item["path"]).parent.name), "description": meta.get("description", ""), "path": item["path"], "metadata": meta})
        return items

    def view(self, name: str, *, reference: str | None = None) -> str:
        for item in self.list():
            if item["name"] != name:
                continue
            base = Path(item["path"]).parent
            target = base / "SKILL.md" if reference is None else base / reference
            if not target.is_file():
                raise FileNotFoundError(target)
            text = target.read_text(encoding="utf-8")
            self._security_scan(text)
            return text
        raise KeyError(name)

    def learn(self, name: str, description: str, procedure: str, *, root: Path | str | None = None, references: Mapping[str, str] | None = None) -> Path:
        if len(description.strip()) > 60:
            raise ValueError("skill description must be <= 60 characters")
        self._security_scan(procedure)
        root_path = Path(root or self.roots[0]).expanduser()
        target = root_path / name
        target.mkdir(parents=True, exist_ok=True)
        skill = "---\n" + f"name: {name}\ndescription: {description.strip()}\nversion: 1.0.0\n" + "---\n\n# " + name.replace("-", " ").title() + "\n\n## When to Use\nUse this skill when the requested task matches its scope.\n\n## Procedure\n" + procedure.strip() + "\n\n## Pitfalls\nReview failures against the repository contract before retrying.\n\n## Verification\nVerify outputs with repository-native checks and explicit evidence.\n"
        out = target / "SKILL.md"
        out.write_text(skill, encoding="utf-8")
        if references:
            ref_dir = target / "references"
            ref_dir.mkdir(exist_ok=True)
            for rel, content in references.items():
                self._security_scan(content)
                path = ref_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return out

    @staticmethod
    def _parse(text: str) -> tuple[dict[str, Any], str]:
        if not text.startswith("---\n"):
            return {}, text
        end = text.find("\n---\n", 4)
        if end < 0:
            raise ValueError("skill front matter is not closed")
        raw = text[4:end]
        meta: dict[str, Any] = {}
        stack: list[tuple[int, dict[str, Any]]] = [(0, meta)]
        for line in raw.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, sep, value = line.strip().partition(":")
            if not sep:
                continue
            while stack and indent < stack[-1][0]:
                stack.pop()
            target = stack[-1][1]
            value = value.strip()
            if not value:
                child: dict[str, Any] = {}
                target[key] = child
                stack.append((indent + 2, child))
            elif value.startswith("[") and value.endswith("]"):
                target[key] = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
            else:
                target[key] = value.strip("\"'")
        return meta, text[end + 6:]

    @staticmethod
    def _security_scan(text: str) -> None:
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS + _INJECTION_PATTERNS):
            raise ValueError("skill contains a suspicious secret or instruction-injection pattern")
        if any(ord(ch) in {0x202A, 0x202B, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069} for ch in text):
            raise ValueError("skill contains bidi control characters")


class ProcessManager:
    """Background process manager with durable completion receipts."""

    def __init__(self, root: Path | str | None = None, *, max_receipts: int = 64, receipt_days: int = 7, output_tail: int = 200_000) -> None:
        self.root = Path(root or (Path.home() / ".aer" / "processes")).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_receipts = max_receipts
        self.receipt_days = receipt_days
        self.output_tail = output_tail
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def start(self, command: Sequence[str], *, cwd: Path | str | None = None, env: Mapping[str, str] | None = None) -> str:
        token = hashlib.sha256(f"{os.getpid()}|{time.time_ns()}|{command}".encode()).hexdigest()[:16]
        proc = subprocess.Popen(list(command), cwd=str(cwd) if cwd else None, env=dict(env) if env else None, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        with self._lock:
            self._processes[token] = proc
            self._meta[token] = {"session_id": token, "command": tuple(command), "started_at": time.time()}
        return token

    def poll(self, session_id: str) -> ProcessReceipt:
        with self._lock:
            proc = self._processes[session_id]
            code = proc.poll()
            if code is None:
                return ProcessReceipt(session_id, self._meta[session_id]["command"], self._meta[session_id]["started_at"], None, None, "", "running")
            output = self._drain(proc)
            receipt = ProcessReceipt(session_id, self._meta[session_id]["command"], self._meta[session_id]["started_at"], time.time(), code, self._redact(output[-self.output_tail:]), "completed" if code == 0 else "failed")
            self._persist_receipt(receipt)
            self._processes.pop(session_id, None)
            self._meta.pop(session_id, None)
            self._prune()
            return receipt

    def wait(self, session_id: str, timeout: float | None = None) -> ProcessReceipt:
        proc = self._processes[session_id]
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TimeoutError(session_id)
        return self.poll(session_id)

    def kill(self, session_id: str) -> None:
        proc = self._processes[session_id]
        if os.name == "nt":
            proc.kill()
        else:
            proc.send_signal(signal.SIGTERM)

    def receipts(self, *, session_id: str | None = None) -> list[ProcessReceipt]:
        result = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if session_id and value.get("session_id") != session_id:
                    continue
                result.append(ProcessReceipt(tuple(value["session_id"]), tuple(value["command"]), value["started_at"], value["finished_at"], value["exit_code"], value["output_tail"], value["status"]))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return result

    @staticmethod
    def _drain(proc: subprocess.Popen[str]) -> str:
        if proc.stdout is None:
            return ""
        return proc.stdout.read() or ""

    def _persist_receipt(self, receipt: ProcessReceipt) -> None:
        path = self.root / f"{receipt.session_id}.json"
        path.write_text(json.dumps(asdict(receipt), indent=2) + "\n", encoding="utf-8")

    def _prune(self) -> None:
        cutoff = time.time() - self.receipt_days * 86400
        files = []
        for path in self.root.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if float(value.get("finished_at", 0)) < cutoff:
                    path.unlink(missing_ok=True)
                else:
                    files.append(path)
            except (OSError, ValueError):
                pass
        for path in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[self.max_receipts:]:
            path.unlink(missing_ok=True)

    @staticmethod
    def _redact(text: str) -> str:
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + "=[REDACTED]", text)
        return text


@dataclass(frozen=True)
class TerminalCommand:
    backend: str
    command: tuple[str, ...]
    cwd: str | None
    environment: Mapping[str, str] = field(default_factory=dict)


class TerminalBackends:
    """Backend-normalized command construction; external backends fail explicitly."""

    BACKENDS = {"local", "docker", "ssh", "singularity", "modal", "daytona", "vercel_sandbox"}

    def __init__(self, backend: str = "local", **config: Any) -> None:
        if backend not in self.BACKENDS:
            raise ValueError(f"unsupported terminal backend: {backend}")
        self.backend = backend
        self.config = dict(config)

    def prepare(self, command: Sequence[str], *, cwd: str | None = None) -> TerminalCommand:
        cmd = tuple(command)
        if self.backend == "local":
            return TerminalCommand(self.backend, cmd, cwd)
        if self.backend == "docker":
            image = self.config.get("image", "python:3.11-slim")
            root = cwd or "/workspace"
            return TerminalCommand(self.backend, ("docker", "exec", "-i", self.config.get("container", "aer-sandbox"), *cmd), root)
        if self.backend == "ssh":
            host = self.config.get("host")
            user = self.config.get("user")
            if not host or not user:
                raise RuntimeError("ssh backend requires host and user")
            shell = shlex.join(list(cmd))
            prefix = f"{user}@{host}"
            return TerminalCommand(self.backend, ("ssh", prefix, shell), cwd)
        if self.backend == "singularity":
            image = self.config.get("image")
            if not image:
                raise RuntimeError("singularity backend requires an image")
            return TerminalCommand(self.backend, ("apptainer", "exec", image, *cmd), cwd)
        if self.backend in {"modal", "daytona", "vercel_sandbox"}:
            executable = self.config.get("executable")
            if not executable:
                raise RuntimeError(f"{self.backend} backend requires an explicit adapter executable")
            return TerminalCommand(self.backend, (executable, *cmd), cwd)
        raise RuntimeError(self.backend)


class DelegationManager:
    """Parallel task runner that is subordinate to TaskPlan dependency semantics."""

    def __init__(self, *, max_concurrent: int = 10, max_depth: int = 1) -> None:
        if max_concurrent < 1 or max_depth < 1:
            raise ValueError("delegation limits must be positive")
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth

    def run(self, plan: TaskPlan, worker: Callable[[Task], Any], *, depth: int = 0) -> list[DelegationReceipt]:
        if depth >= self.max_depth:
            raise RuntimeError("delegation depth limit reached")
        results: list[DelegationReceipt] = []
        pending = {task.id: task for task in plan.tasks}
        done: set[str] = set()
        while pending:
            ready = [task for task in pending.values() if all(dep in done for dep in task.dependencies)]
            if not ready:
                raise RuntimeError("delegation plan is blocked or cyclic")
            batch = ready[: self.max_concurrent]
            with ThreadPoolExecutor(max_workers=min(self.max_concurrent, len(batch))) as pool:
                future_map = {pool.submit(worker, task): task for task in batch}
                for future in as_completed(future_map):
                    task = future_map[future]
                    started = time.time()
                    try:
                        output = future.result()
                        results.append(DelegationReceipt(task.id, "passed", started, time.time(), 1, output))
                        done.add(task.id)
                    except Exception as exc:
                        results.append(DelegationReceipt(task.id, "failed", started, time.time(), 1, error=f"{type(exc).__name__}: {exc}"))
                        done.add(task.id)
            for task in batch:
                pending.pop(task.id, None)
        return results


class CronStore:
    """Durable scheduler records; execution remains under AER runtime policy."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or (Path.home() / ".aer" / "cron" / "jobs.json" )).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def list(self) -> list[CronJob]:
        with self._lock:
            if not self.path.exists():
                return []
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [CronJob(**row) for row in raw]

    def upsert(self, job: CronJob) -> None:
        with self._lock:
            rows = [item for item in self.list() if item.job_id != job.job_id]
            rows.append(job)
            self.path.write_text(json.dumps([asdict(item) for item in sorted(rows, key=lambda x: x.job_id)], indent=2) + "\n", encoding="utf-8")

    def pause(self, job_id: str) -> CronJob:
        return self._set_enabled(job_id, False)

    def resume(self, job_id: str) -> CronJob:
        return self._set_enabled(job_id, True)

    def due(self, now: float | None = None) -> list[CronJob]:
        point = now or time.time()
        return [job for job in self.list() if job.enabled and job.next_run_at is not None and job.next_run_at <= point]

    def record_run(self, job_id: str, *, status: str, next_run_at: float | None) -> CronJob:
        jobs = self.list()
        match = next(item for item in jobs if item.job_id == job_id)
        updated = CronJob(match.job_id, match.name, match.schedule, match.task_id, match.enabled, next_run_at, time.time(), status)
        self.upsert(updated)
        return updated

    def _set_enabled(self, job_id: str, enabled: bool) -> CronJob:
        jobs = self.list()
        match = next((item for item in jobs if item.job_id == job_id), None)
        if match is None:
            raise KeyError(job_id)
        updated = CronJob(match.job_id, match.name, match.schedule, match.task_id, enabled, match.next_run_at, match.last_run_at, match.last_status)
        self.upsert(updated)
        return updated


class OutputQualityGate:
    """Final-output guardrail focused on truthful, useful and reproducible results."""

    REQUIRED_FIELDS = ("outcome", "changed_files", "verification", "evidence")

    def evaluate(self, report: Mapping[str, Any], *, changed_files: Sequence[str] = ()) -> QualityReport:
        findings: list[QualityFinding] = []
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in report or report[field_name] in (None, "", [], {}):
                findings.append(QualityFinding("error", "missing_report_field", f"completion report missing {field_name}"))
        verification = report.get("verification", {})
        if isinstance(verification, Mapping):
            if verification.get("passed") is not True and not verification.get("blocked_reason"):
                findings.append(QualityFinding("error", "verification_missing", "output claims completion without explicit verification or a blocking reason"))
        if report.get("claims_passed") and not report.get("evidence"):
            findings.append(QualityFinding("error", "claim_without_evidence", "success claims require evidence"))
        if len(set(changed_files)) != len(list(changed_files)):
            findings.append(QualityFinding("warning", "duplicate_changed_path", "changed file list contains duplicates"))
        return QualityReport(not any(item.severity == "error" for item in findings), tuple(findings))


class HermesCapabilityRuntime:
    """Single facade composing the capability layer for AdaptiveRuntime."""

    def __init__(self, *, state_root: Path | str | None = None, skill_roots: Sequence[Path | str] = ()) -> None:
        root = Path(state_root or (Path.home() / ".aer")).expanduser()
        self.registry = CapabilityRegistry()
        self.memory = MemoryStore(root / "memory")
        self.skills = SkillRegistry(skill_roots or (root / "skills",))
        self.processes = ProcessManager(root / "processes")
        self.cron = CronStore(root / "cron" / "jobs.json")
        self.delegation = DelegationManager()
        self.quality = OutputQualityGate()

    def discover(self, provider_states: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, CapabilityState]:
        return self.registry.discover(provider_states)

    def session_boundary(self, session_id: str, messages: Sequence[tuple[str, str]]) -> None:
        self.memory.index_session(session_id, messages)

    def readiness(self) -> dict[str, Any]:
        states = self.registry.discover()
        return {
            "capabilities": self.registry.export(),
            "skills": self.skills.list(),
            "cron_jobs": [asdict(job) for job in self.cron.list()],
            "process_receipts": [asdict(receipt) for receipt in self.processes.receipts()[:8]],
            "memory": {"memory_chars": sum(len(x.content) for x in self.memory.list("memory")), "user_chars": sum(len(x.content) for x in self.memory.list("user"))},
            "ready": all(state.status != "unavailable" for name, state in states.items() if name in {"search", "terminal", "file", "skills", "memory", "todo", "session_search", "delegation"}),
        }


__all__ = [
    "CAPABILITY_NAMES", "TOOLSET_PRESETS", "CapabilityRegistry", "CapabilitySpec", "CapabilityState",
    "MemoryStore", "MemoryEntry", "MemoryMutation", "SessionMessage", "SkillRegistry",
    "ProcessManager", "ProcessReceipt", "TerminalBackends", "TerminalCommand", "DelegationManager",
    "DelegationReceipt", "CronStore", "CronJob", "OutputQualityGate", "QualityFinding", "QualityReport",
    "HermesCapabilityRuntime",
]
