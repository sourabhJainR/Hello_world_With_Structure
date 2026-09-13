"""Canonical AER capability core inspired by Hermes Agent.

One implementation surface for memory, session recall, skills, toolsets,
background work, delegation, scheduling, terminal backends and output quality.
AER keeps authority over intent, security, evidence, verification and learning.
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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .task_planner import Task, TaskPlan

CAPABILITY_NAMES = (
    "web", "x_search", "search", "terminal", "file", "browser", "vision", "image_gen", "skills", "tts",
    "todo", "memory", "session_search", "cronjob", "code_execution", "delegation", "clarify", "mcp",
)
TOOLSET_PRESETS = {
    "safe": ("file", "search", "memory", "session_search", "todo"),
    "coding": ("terminal", "file", "search", "skills", "memory", "session_search", "delegation", "code_execution"),
    "research": ("web", "x_search", "search", "file", "browser", "memory", "session_search", "delegation"),
    "automation": ("terminal", "file", "cronjob", "memory", "session_search"),
    "full": CAPABILITY_NAMES,
}
_BIDI = {0x202A, 0x202B, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
_SENSITIVE = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*['\"]?[^\s,;'\"]+"),
    re.compile(r"-----BEGIN [A-Z0-9 ]+ PRIVATE KEY-----"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{16,}\b"),
)
_INJECTION = (
    re.compile(r"(?i)ignore\s+(all|previous|prior)\s+instructions"),
    re.compile(r"(?i)\b(exfiltrat|steal\s+the\s+credentials)"),
)

@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    builtin: bool = False
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
    _BUILTIN = {"search", "terminal", "file", "skills", "todo", "memory", "session_search", "cronjob", "code_execution", "delegation", "clarify"}
    SPECS = {name: CapabilitySpec(name, name.replace("_", " "), builtin=name in _BUILTIN) for name in CAPABILITY_NAMES}
    SPECS["web"] = CapabilitySpec("web", "web retrieval and extraction", fallback="search")
    SPECS["x_search"] = CapabilitySpec("x_search", "social/web search", fallback="search")
    SPECS["mcp"] = CapabilitySpec("mcp", "external tool interoperability", risk="high")

    def __init__(self) -> None:
        self._states: dict[str, CapabilityState] = {}

    def register(self, name: str, status: str, *, provider: str = "aer", reason: str = "", evidence: Iterable[str] = ()) -> None:
        if name not in self.SPECS or status not in {"native", "fallback", "unavailable"}:
            raise ValueError(f"invalid capability registration: {name}/{status}")
        self._states[name] = CapabilityState(name, status, provider, reason, tuple(sorted(set(evidence))))

    def discover(self, explicit: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, CapabilityState]:
        explicit = explicit or {}
        for name, spec in self.SPECS.items():
            item = explicit.get(name)
            if item:
                self.register(name, str(item.get("status", "unavailable")), provider=str(item.get("provider", "aer")), reason=str(item.get("reason", "")), evidence=item.get("evidence", ()))
            elif spec.builtin:
                self.register(name, "fallback", reason="AER canonical implementation")
            else:
                self.register(name, "unavailable", reason="no verified adapter configured")
        return dict(self._states)

    def require(self, name: str) -> CapabilityState:
        if name not in self._states:
            self.discover()
        state = self._states[name]
        if state.status == "unavailable":
            fallback = self.SPECS[name].fallback
            if fallback and fallback in self._states and self._states[fallback].status != "unavailable":
                return self._states[fallback]
            raise RuntimeError(f"capability unavailable: {name}; {state.reason}")
        return state

    def toolset(self, name: str) -> tuple[str, ...]:
        if name not in TOOLSET_PRESETS:
            raise ValueError(f"unknown toolset: {name}")
        return tuple(TOOLSET_PRESETS[name])

    def export(self) -> dict[str, Any]:
        return {name: asdict(state) for name, state in sorted(self._states.items())}

class MemoryStore:
    """Bounded durable memory with exact FTS5 session recall and approval staging."""
    def __init__(self, root: Path | str | None = None, *, memory_limit: int = 2200, user_limit: int = 1375) -> None:
        self.root = Path(root or Path.home() / ".aer" / "memory").expanduser(); self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "state.db"; self.memory_limit, self.user_limit = memory_limit, user_limit; self._lock = threading.RLock()
        with sqlite3.connect(self.db) as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memory(entry_id TEXT PRIMARY KEY, target TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, source TEXT NOT NULL, intent_digest TEXT);
                CREATE UNIQUE INDEX IF NOT EXISTS ux_memory_content ON memory(target, content);
                CREATE TABLE IF NOT EXISTS pending_mutations(mutation_id TEXT PRIMARY KEY, action TEXT NOT NULL, target TEXT NOT NULL, content TEXT, old_text TEXT, created_at REAL NOT NULL, source TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS session_messages(session_id TEXT NOT NULL, seq INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL, PRIMARY KEY(session_id, seq));
                CREATE VIRTUAL TABLE IF NOT EXISTS session_fts USING fts5(session_id UNINDEXED, seq UNINDEXED, role, content);
            """)

    @staticmethod
    def _scan(text: str) -> None:
        if any(p.search(text) for p in _SENSITIVE + _INJECTION) or any(ord(ch) in _BIDI for ch in text):
            raise ValueError("content rejected by memory security scan")

    def _limit(self, target: str) -> int:
        if target not in {"memory", "user"}: raise ValueError("target must be memory or user")
        return self.memory_limit if target == "memory" else self.user_limit

    def list(self, target: str) -> list[MemoryEntry]:
        self._limit(target)
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return [MemoryEntry(**dict(row)) for row in conn.execute("SELECT * FROM memory WHERE target=? ORDER BY updated_at DESC", (target,))]

    def add(self, target: str, content: str, *, source: str = "agent", intent_digest: str | None = None, approval_required: bool = False) -> MemoryEntry | MemoryMutation:
        self._scan(content)
        with self._lock:
            items = self.list(target); duplicate = next((item for item in items if item.content == content), None)
            if duplicate: return duplicate
            if sum(len(item.content) for item in items) + len(content) > self._limit(target): raise ValueError(f"{target} memory capacity exceeded; consolidate before adding")
            return self._stage("add", target, content, None, source) if approval_required else self._insert(target, content, source, intent_digest)

    def replace(self, target: str, old_text: str, content: str, *, source: str = "agent", approval_required: bool = False) -> MemoryEntry | MemoryMutation:
        self._scan(content); matches = [item for item in self.list(target) if old_text in item.content]
        if len(matches) != 1: raise ValueError(f"replace requires exactly one matching entry; found {len(matches)}")
        if approval_required: return self._stage("replace", target, content, old_text, source)
        with sqlite3.connect(self.db) as conn: conn.execute("DELETE FROM memory WHERE entry_id=?", (matches[0].entry_id,))
        return self._insert(target, content, source, matches[0].intent_digest)

    def remove(self, target: str, old_text: str, *, source: str = "agent", approval_required: bool = False) -> MemoryMutation | bool:
        matches = [item for item in self.list(target) if old_text in item.content]
        if len(matches) != 1: raise ValueError(f"remove requires exactly one matching entry; found {len(matches)}")
        if approval_required: return self._stage("remove", target, None, old_text, source)
        with sqlite3.connect(self.db) as conn: conn.execute("DELETE FROM memory WHERE entry_id=?", (matches[0].entry_id,))
        return True

    def pending(self) -> list[MemoryMutation]:
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return [MemoryMutation(**{**dict(row), "approved": bool(row["approved"])}) for row in conn.execute("SELECT * FROM pending_mutations WHERE approved=0 ORDER BY created_at")]

    def approve(self, mutation_id: str) -> MemoryEntry | bool:
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row; row = conn.execute("SELECT * FROM pending_mutations WHERE mutation_id=?", (mutation_id,)).fetchone()
        if not row: raise KeyError(mutation_id)
        action = row["action"]
        if action == "add": result = self.add(row["target"], row["content"], source=row["source"])
        elif action == "replace": result = self.replace(row["target"], row["old_text"], row["content"], source=row["source"])
        elif action == "remove": result = self.remove(row["target"], row["old_text"], source=row["source"])
        else: raise ValueError(action)
        with sqlite3.connect(self.db) as conn: conn.execute("DELETE FROM pending_mutations WHERE mutation_id=?", (mutation_id,))
        return result

    def reject(self, mutation_id: str) -> None:
        with sqlite3.connect(self.db) as conn: conn.execute("DELETE FROM pending_mutations WHERE mutation_id=?", (mutation_id,))

    def index_session(self, session_id: str, messages: Sequence[tuple[str, str]]) -> None:
        with sqlite3.connect(self.db) as conn:
            for seq, (role, content) in enumerate(messages, 1):
                if conn.execute("SELECT 1 FROM session_messages WHERE session_id=? AND seq=?", (session_id, seq)).fetchone(): continue
                now = time.time(); conn.execute("INSERT INTO session_messages VALUES(?,?,?,?,?)", (session_id, seq, role, content, now)); conn.execute("INSERT INTO session_fts VALUES(?,?,?,?)", (session_id, seq, role, content))

    def search_session(self, query: str, *, limit: int = 20) -> list[SessionMessage]:
        if not query.strip(): return []
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row; rows = conn.execute("SELECT session_id, seq, role, content FROM session_fts WHERE session_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit)); out = []
            for row in rows:
                stamp = conn.execute("SELECT created_at FROM session_messages WHERE session_id=? AND seq=?", (row["session_id"], row["seq"])).fetchone()[0]; out.append(SessionMessage(row["session_id"], int(row["seq"]), row["role"], row["content"], float(stamp)))
            return out

    def _entry(self, target: str, content: str, source: str, intent_digest: str | None) -> MemoryEntry:
        now = time.time(); return MemoryEntry(hashlib.sha256(f"{target}|{content}".encode()).hexdigest()[:16], target, content, now, now, source, intent_digest)

    def _insert(self, target: str, content: str, source: str, intent_digest: str | None) -> MemoryEntry:
        entry = self._entry(target, content, source, intent_digest)
        with sqlite3.connect(self.db) as conn: conn.execute("INSERT OR IGNORE INTO memory VALUES(?,?,?,?,?,?,?)", asdict(entry).values())
        return entry

    def _stage(self, action: str, target: str, content: str | None, old_text: str | None, source: str) -> MemoryMutation:
        mutation = MemoryMutation(hashlib.sha256(f"{action}|{target}|{content}|{old_text}|{time.time_ns()}".encode()).hexdigest()[:16], action, target, content, old_text, time.time(), source, False)
        with sqlite3.connect(self.db) as conn: conn.execute("INSERT INTO pending_mutations VALUES(?,?,?,?,?,?,?,0)", (mutation.mutation_id, mutation.action, mutation.target, mutation.content, mutation.old_text, mutation.created_at, mutation.source))
        return mutation

class SkillRegistry:
    """Progressive-disclosure skills with conditional activation and safe learning."""
    def __init__(self, roots: Sequence[Path | str]): self.roots = [Path(r).expanduser() for r in roots]
    def scan(self) -> list[dict[str, Any]]:
        out=[]
        for root in self.roots:
            if not root.is_dir(): continue
            for path in sorted(root.rglob("SKILL.md")):
                try:
                    text=path.read_text(encoding="utf-8"); meta, body=self._parse(text); self._scan_security(text); out.append({"path":str(path),"status":"ready","metadata":meta,"description":meta.get("description",""),"body_chars":len(body)})
                except (OSError,UnicodeError,ValueError) as exc: out.append({"path":str(path),"status":"invalid","error":str(exc)})
        return out
    def list(self, *, available_tools: Iterable[str]=(), platform: str|None=None) -> list[dict[str,Any]]:
        tools=set(available_tools); out=[]
        for item in self.scan():
            if item["status"]!="ready": continue
            meta=item["metadata"]; platforms=set(meta.get("platforms",()) or ())
            if platform and platforms and platform not in platforms: continue
            nested=meta.get("metadata",{}); policy=nested.get("aer",nested.get("hermes",{})) if isinstance(nested,dict) else {}; policy=policy if isinstance(policy,dict) else {}
            required=set(policy.get("requires_tools",()) or ()) | set(policy.get("requires_toolsets",()) or ()); fallback=set(policy.get("fallback_for_tools",()) or ()) | set(policy.get("fallback_for_toolsets",()) or ())
            if required and not required.issubset(tools): continue
            if fallback and fallback.intersection(tools): continue
            out.append({"name":meta.get("name",Path(item["path"]).parent.name),"description":meta.get("description",""),"path":item["path"],"metadata":meta})
        return out
    def view(self,name:str,*,reference:str|None=None)->str:
        item=next((x for x in self.scan() if x.get("status")=="ready" and x["metadata"].get("name",Path(x["path"]).parent.name)==name),None)
        if not item: raise KeyError(name)
        target=Path(item["path"]).parent/(reference or "SKILL.md"); text=target.read_text(encoding="utf-8"); self._scan_security(text); return text
    def learn(self,name:str,description:str,procedure:str,*,root:Path|str|None=None,references:Mapping[str,str]|None=None)->Path:
        if not 1<=len(description.strip())<=60: raise ValueError("skill description must be 1-60 characters")
        self._scan_security(procedure); target=Path(root or self.roots[0]).expanduser()/name; target.mkdir(parents=True,exist_ok=True)
        (target/"SKILL.md").write_text(f"---\nname: {name}\ndescription: {description.strip()}\nversion: 1.0.0\n---\n\n# {name.replace('-', ' ').title()}\n\n## When to Use\nUse when the request matches this skill scope.\n\n## Procedure\n{procedure.strip()}\n\n## Verification\nVerify with repository-native checks and evidence.\n",encoding="utf-8")
        for rel,content in (references or {}).items(): self._scan_security(content); p=target/"references"/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
        return target/"SKILL.md"
    @staticmethod
    def _parse(text:str)->tuple[dict[str,Any],str]:
        if not text.startswith("---\n"): return {},text
        end=text.find("\n---\n",4)
        if end<0: raise ValueError("unclosed skill front matter")
        meta={}; stack=[(0,meta)]
        for line in text[4:end].splitlines():
            if not line.strip() or line.lstrip().startswith("#"): continue
            indent=len(line)-len(line.lstrip()); key,sep,raw=line.strip().partition(":")
            if not sep: continue
            while stack and indent<stack[-1][0]: stack.pop()
            target=stack[-1][1]; raw=raw.strip()
            if not raw: child={}; target[key]=child; stack.append((indent+2,child))
            elif raw.startswith("[") and raw.endswith("]"): target[key]=[x.strip().strip("\"'") for x in raw[1:-1].split(",") if x.strip()]
            else: target[key]=raw.strip("\"'")
        return meta,text[end+5:]
    @staticmethod
    def _scan_security(text:str)->None:
        if any(p.search(text) for p in _SENSITIVE+_INJECTION) or any(ord(ch) in _BIDI for ch in text): raise ValueError("skill rejected by security scan")

class ProcessManager:
    """Background process handles with bounded, redacted durable receipts."""
    def __init__(self,root:Path|str|None=None,*,max_receipts:int=64,receipt_days:int=7,output_tail:int=200_000)->None:
        self.root=Path(root or Path.home()/".aer"/"processes").expanduser(); self.root.mkdir(parents=True,exist_ok=True); self.max_receipts,self.receipt_days,self.output_tail=max_receipts,receipt_days,output_tail; self._processes={}; self._meta={}; self._lock=threading.RLock()
    def start(self,command:Sequence[str],*,cwd:Path|str|None=None,env:Mapping[str,str]|None=None)->str:
        sid=hashlib.sha256(f"{time.time_ns()}|{command}".encode()).hexdigest()[:16]; proc=subprocess.Popen(list(command),cwd=str(cwd) if cwd else None,env=dict(env) if env else None,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        with self._lock:self._processes[sid]=proc; self._meta[sid]={"command":tuple(command),"started_at":time.time()}
        return sid
    def poll(self,session_id:str)->ProcessReceipt:
        with self._lock:
            proc=self._processes[session_id]; code=proc.poll()
            if code is None:return ProcessReceipt(session_id,self._meta[session_id]["command"],self._meta[session_id]["started_at"],None,None,"","running")
            try: output=proc.stdout.read() if proc.stdout else ""
            finally:
                if proc.stdout: proc.stdout.close()
            receipt=ProcessReceipt(session_id,self._meta[session_id]["command"],self._meta[session_id]["started_at"],time.time(),code,self._redact(output[-self.output_tail:]),"completed" if code==0 else "failed"); self._persist(receipt); self._processes.pop(session_id,None); self._meta.pop(session_id,None); self._prune(); return receipt
    def wait(self,session_id:str,timeout:float|None=None)->ProcessReceipt:
        try:self._processes[session_id].wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:raise TimeoutError(session_id) from exc
        return self.poll(session_id)
    def kill(self,session_id:str)->None:
        proc=self._processes[session_id]; proc.kill() if os.name=="nt" else proc.send_signal(signal.SIGTERM)
    def receipts(self,*,session_id:str|None=None)->list[ProcessReceipt]:
        out=[]
        for path in sorted(self.root.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True):
            try:
                value=json.loads(path.read_text(encoding="utf-8")); sid=str(value["session_id"])
                if session_id and sid!=session_id:continue
                out.append(ProcessReceipt(sid,tuple(value["command"]),float(value["started_at"]),value.get("finished_at"),value.get("exit_code"),value.get("output_tail",""),value.get("status","completed")))
            except (OSError,ValueError,KeyError,TypeError):pass
        return out
    def _persist(self,receipt:ProcessReceipt)->None:(self.root/f"{receipt.session_id}.json").write_text(json.dumps(asdict(receipt),indent=2)+"\n",encoding="utf-8")
    def _prune(self)->None:
        cutoff=time.time()-self.receipt_days*86400; paths=[]
        for path in self.root.glob("*.json"):
            try:
                value=json.loads(path.read_text(encoding="utf-8")); finished=float(value.get("finished_at",0))
                if finished<cutoff:path.unlink(missing_ok=True)
                else:paths.append(path)
            except (OSError,ValueError):pass
        for path in sorted(paths,key=lambda p:p.stat().st_mtime,reverse=True)[self.max_receipts:]:path.unlink(missing_ok=True)
    @staticmethod
    def _redact(text:str)->str:
        for pattern in _SENSITIVE:text=pattern.sub("[REDACTED]",text)
        return text

@dataclass(frozen=True)
class TerminalCommand:
    backend:str
    command:tuple[str,...]
    cwd:str|None

class TerminalBackends:
    BACKENDS={"local","docker","ssh","singularity","modal","daytona","vercel_sandbox"}
    def __init__(self,backend:str="local",**config:Any):
        if backend not in self.BACKENDS:raise ValueError(f"unsupported terminal backend: {backend}")
        self.backend,self.config=backend,dict(config)
    def prepare(self,command:Sequence[str],*,cwd:str|None=None)->TerminalCommand:
        cmd=tuple(command)
        if self.backend=="local":return TerminalCommand(self.backend,cmd,cwd)
        if self.backend=="docker":return TerminalCommand(self.backend,("docker","exec","-i",self.config.get("container","aer-sandbox"),*cmd),cwd or "/workspace")
        if self.backend=="ssh":
            if not self.config.get("host") or not self.config.get("user"):raise RuntimeError("ssh backend requires host and user")
            return TerminalCommand(self.backend,("ssh",f"{self.config['user']}@{self.config['host']}",shlex.join(cmd)),cwd)
        if self.backend=="singularity":
            if not self.config.get("image"):raise RuntimeError("singularity backend requires image")
            return TerminalCommand(self.backend,("apptainer","exec",self.config["image"],*cmd),cwd)
        if not self.config.get("executable"):raise RuntimeError(f"{self.backend} backend requires an explicit adapter executable")
        return TerminalCommand(self.backend,(self.config["executable"],*cmd),cwd)

class DelegationManager:
    """Dependency-aware parallel delegation; failed prerequisites block dependents."""
    def __init__(self,*,max_concurrent:int=10,max_depth:int=1):
        if max_concurrent<1 or max_depth<1:raise ValueError("delegation limits must be positive")
        self.max_concurrent,self.max_depth=max_concurrent,max_depth
    def run(self,plan:TaskPlan,worker:Callable[[Task],Any],*,depth:int=0)->list[DelegationReceipt]:
        if depth>=self.max_depth:raise RuntimeError("delegation depth limit reached")
        pending=dict(plan.tasks); done=set(); blocked=set(); receipts=[]
        while pending:
            ready=sorted([t for t in pending.values() if not any(dep in blocked for dep in t.dependencies) and all(plan.tasks[d].status=="done" or d in done for d in t.dependencies)],key=lambda t:t.id)
            if not ready:
                for t in pending.values():
                    if any(dep in blocked for dep in t.dependencies):t.status="blocked"; blocked.add(t.id)
                break
            batch=ready[:self.max_concurrent]
            with ThreadPoolExecutor(max_workers=min(self.max_concurrent,len(batch))) as pool:
                futures={pool.submit(worker,t):t for t in batch}
                for future in as_completed(futures):
                    task=futures[future]; started=time.time()
                    try:output=future.result(); task.status="done"; done.add(task.id); receipts.append(DelegationReceipt(task.id,"passed",started,time.time(),1,output))
                    except Exception as exc:task.status="blocked"; blocked.add(task.id); receipts.append(DelegationReceipt(task.id,"failed",started,time.time(),1,error=f"{type(exc).__name__}: {exc}"))
            for task in batch:pending.pop(task.id,None)
        return receipts

class CronStore:
    def __init__(self,path:Path|str|None=None):self.path=Path(path or Path.home()/".aer"/"cron"/"jobs.json").expanduser();self.path.parent.mkdir(parents=True,exist_ok=True);self._lock=threading.RLock()
    def list(self)->list[CronJob]:
        if not self.path.exists():return []
        return [CronJob(**row) for row in json.loads(self.path.read_text(encoding="utf-8"))]
    def upsert(self,job:CronJob)->None:
        with self._lock:
            rows=[x for x in self.list() if x.job_id!=job.job_id]+[job]; self.path.write_text(json.dumps([asdict(x) for x in sorted(rows,key=lambda x:x.job_id)],indent=2)+"\n",encoding="utf-8")
    def pause(self,job_id:str)->CronJob:return self._set(job_id,False)
    def resume(self,job_id:str)->CronJob:return self._set(job_id,True)
    def due(self,now:float|None=None)->list[CronJob]:return [x for x in self.list() if x.enabled and x.next_run_at is not None and x.next_run_at <= (now or time.time())]
    def record_run(self,job_id:str,*,status:str,next_run_at:float|None)->CronJob:
        current=next(x for x in self.list() if x.job_id==job_id);updated=CronJob(current.job_id,current.name,current.schedule,current.task_id,current.enabled,next_run_at,time.time(),status);self.upsert(updated);return updated
    def _set(self,job_id:str,enabled:bool)->CronJob:
        current=next((x for x in self.list() if x.job_id==job_id),None)
        if current is None:raise KeyError(job_id)
        updated=CronJob(current.job_id,current.name,current.schedule,current.task_id,enabled,current.next_run_at,current.last_run_at,current.last_status);self.upsert(updated);return updated

class OutputQualityGate:
    REQUIRED=("outcome","changed_files","verification","evidence")
    def evaluate(self,report:Mapping[str,Any],*,changed_files:Sequence[str]=())->QualityReport:
        findings=[]
        for name in self.REQUIRED:
            if report.get(name) in (None,"",[],{}):findings.append(QualityFinding("error","missing_report_field",f"completion report missing {name}"))
        verification=report.get("verification",{})
        if isinstance(verification,Mapping) and verification.get("passed") is not True and not verification.get("blocked_reason"):findings.append(QualityFinding("error","verification_missing","completion requires verification evidence or a blocking reason"))
        if report.get("claims_passed") and not report.get("evidence"):findings.append(QualityFinding("error","claim_without_evidence","success claims require evidence"))
        if len(set(changed_files))!=len(list(changed_files)):findings.append(QualityFinding("warning","duplicate_changed_path","changed file list contains duplicates"))
        return QualityReport(not any(x.severity=="error" for x in findings),tuple(findings))

class HermesCapabilityRuntime:
    """Composition root for the unified operational capability surface."""
    def __init__(self,*,state_root:Path|str|None=None,skill_roots:Sequence[Path|str]=()):
        root=Path(state_root or Path.home()/".aer").expanduser();self.registry=CapabilityRegistry();self.memory=MemoryStore(root/"memory");self.skills=SkillRegistry(skill_roots or (root/"skills",));self.processes=ProcessManager(root/"processes");self.cron=CronStore(root/"cron"/"jobs.json");self.delegation=DelegationManager();self.quality=OutputQualityGate()
    def discover(self,provider_states:Mapping[str,Mapping[str,Any]]|None=None):return self.registry.discover(provider_states)
    def session_boundary(self,session_id:str,messages:Sequence[tuple[str,str]]):self.memory.index_session(session_id,messages)
    def readiness(self)->dict[str,Any]:
        states=self.registry.discover();return {"capabilities":self.registry.export(),"skills":self.skills.list(),"cron_jobs":[asdict(x) for x in self.cron.list()],"process_receipts":[asdict(x) for x in self.processes.receipts()[:8]],"memory":{"memory_chars":sum(len(x.content) for x in self.memory.list("memory")),"user_chars":sum(len(x.content) for x in self.memory.list("user"))},"ready":all(states[name].status!="unavailable" for name in ("search","terminal","file","skills","memory","todo","session_search","delegation"))}

__all__=["CAPABILITY_NAMES","TOOLSET_PRESETS","CapabilityRegistry","CapabilitySpec","CapabilityState","MemoryStore","MemoryEntry","MemoryMutation","SessionMessage","SkillRegistry","ProcessManager","ProcessReceipt","TerminalBackends","TerminalCommand","DelegationManager","DelegationReceipt","CronStore","CronJob","OutputQualityGate","QualityFinding","QualityReport","HermesCapabilityRuntime"]
