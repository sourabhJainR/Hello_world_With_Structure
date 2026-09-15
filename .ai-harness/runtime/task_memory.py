#!/usr/bin/env python3
"""Versioned, evidence-backed durable learning ledger with concurrency guards."""
from __future__ import annotations
import hashlib,json,os,sqlite3,time
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterator
SCHEMA_VERSION=2; LEARNING_VERSION="2.0"
CATEGORIES={"command","approach","bug","feature","regression","environment","verification"}
OUTCOMES={"worked","failed","partial","not-applicable","regressed"}; PROMOTIONS={"candidate","verified","superseded","rejected"}; MAX_FIELD=8000

def _clean(value:Any,limit:int=MAX_FIELD)->str:
    text=str(value or "").strip(); return text if len(text)<=limit else text[:limit-40]+" ...[guardrail-trimmed]"
def _id(category,task,command,approach,detail): return "tm-"+hashlib.sha256("|".join((category,task,command,approach,detail)).encode()).hexdigest()[:20]
@contextmanager
def _process_lock(path:Path)->Iterator[None]:
    path.parent.mkdir(parents=True,exist_ok=True); h=path.open("a+")
    try:
        if os.name=="nt": import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_LOCK,1)
        else: import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_EX)
        yield
    finally:
        if os.name=="nt": import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_UNLCK,1)
        else: import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_UN)
        h.close()
def _db_path(root:Path)->Path:
    p=Path(root)/".ai-harness"/"learning"/"task-memory.sqlite3"; p.parent.mkdir(parents=True,exist_ok=True); return p

def _connect(root:Path)->sqlite3.Connection:
    db=sqlite3.connect(_db_path(root),timeout=30,isolation_level=None); db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA busy_timeout=30000"); db.execute("PRAGMA synchronous=NORMAL")
    db.execute("""CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, recorded_at INTEGER NOT NULL, task TEXT NOT NULL, category TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL, command TEXT, approach TEXT, construct_refs TEXT NOT NULL, run_id TEXT, evidence_ids TEXT NOT NULL, status TEXT NOT NULL, promotion TEXT NOT NULL, schema_version INTEGER NOT NULL DEFAULT 1, learning_version TEXT NOT NULL DEFAULT '1.1', revision INTEGER NOT NULL DEFAULT 1, supersedes_id TEXT, fingerprint TEXT, source_agent TEXT, verified_at INTEGER)""")
    cols={r[1] for r in db.execute("PRAGMA table_info(observations)")}
    additions={"schema_version":"INTEGER NOT NULL DEFAULT 1","learning_version":"TEXT NOT NULL DEFAULT '1.1'","revision":"INTEGER NOT NULL DEFAULT 1","supersedes_id":"TEXT","fingerprint":"TEXT","source_agent":"TEXT","verified_at":"INTEGER"}
    for name,definition in additions.items():
        if name not in cols: db.execute(f"ALTER TABLE observations ADD COLUMN {name} {definition}")
    db.execute("CREATE INDEX IF NOT EXISTS idx_observations_task ON observations(task)"); db.execute("CREATE INDEX IF NOT EXISTS idx_observations_task_promotion ON observations(task,promotion)"); db.execute("CREATE INDEX IF NOT EXISTS idx_observations_outcome ON observations(outcome)"); db.execute("CREATE INDEX IF NOT EXISTS idx_observations_fingerprint ON observations(fingerprint)")
    return db

def record(root:Path,*,task:str,category:str,outcome:str,detail:str,command:str|None=None,approach:str|None=None,construct_refs:list[str]|None=None,run_id:str|None=None,evidence_ids:list[str]|None=None,source_agent:str|None=None,promotion:str="candidate")->dict[str,Any]:
    if category not in CATEGORIES: raise ValueError(f"unsupported memory category: {category}")
    if outcome not in OUTCOMES: raise ValueError(f"unsupported outcome: {outcome}")
    if promotion not in PROMOTIONS: raise ValueError(f"unsupported promotion state: {promotion}")
    task_clean,detail_clean=_clean(task,1000),_clean(detail); command_clean=_clean(command,1000) if command else None; approach_clean=_clean(approach,1600) if approach else None
    refs=sorted(set(str(x).strip() for x in (construct_refs or []) if str(x).strip())); evidence=sorted(set(str(x).strip() for x in (evidence_ids or []) if str(x).strip()))
    fingerprint=hashlib.sha256(json.dumps([task_clean,category,outcome,command_clean,approach_clean,detail_clean,refs,evidence],sort_keys=True).encode()).hexdigest(); memory_id=_id(category,task_clean,command_clean or "",approach_clean or "",detail_clean); now=int(time.time())
    row={"id":memory_id,"schema_version":SCHEMA_VERSION,"learning_version":LEARNING_VERSION,"recorded_at":now,"task":task_clean,"category":category,"outcome":outcome,"detail":detail_clean,"command":command_clean,"approach":approach_clean,"construct_refs":refs,"run_id":str(run_id) if run_id else None,"evidence_ids":evidence,"status":"observation","promotion":promotion,"revision":1,"supersedes_id":None,"fingerprint":fingerprint,"source_agent":_clean(source_agent,300) if source_agent else None,"verified_at":now if promotion=="verified" else None}
    root=Path(root); dbp=_db_path(root); audit=dbp.with_name("task-memory.jsonl")
    with _process_lock(dbp.with_name("task-memory.lock")):
        with _connect(root) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing=db.execute("SELECT id FROM observations WHERE fingerprint=?",(fingerprint,)).fetchone()
                if existing: row["id"]=existing[0]; db.execute("COMMIT"); return row
                db.execute("""INSERT INTO observations (id,recorded_at,task,category,outcome,detail,command,approach,construct_refs,run_id,evidence_ids,status,promotion,schema_version,learning_version,revision,supersedes_id,fingerprint,source_agent,verified_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(row["id"],now,task_clean,category,outcome,detail_clean,command_clean,approach_clean,json.dumps(refs),row["run_id"],json.dumps(evidence),"observation",promotion,SCHEMA_VERSION,LEARNING_VERSION,1,None,fingerprint,row["source_agent"],row["verified_at"]))
                db.execute("COMMIT")
            except Exception: db.execute("ROLLBACK"); raise
        with audit.open("a",encoding="utf-8") as h: h.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
    return row

def relevant(root:Path,task:str,limit:int=20)->list[dict[str,Any]]:
    dbp=_db_path(Path(root)); terms={x.lower() for x in task.split() if len(x)>2}; found=[]
    with _process_lock(dbp.with_name("task-memory.lock")):
        with _connect(Path(root)) as db:
            for raw in db.execute("SELECT id,recorded_at,task,category,outcome,detail,command,approach,construct_refs,run_id,evidence_ids,status,promotion,schema_version,learning_version,revision,supersedes_id,source_agent,verified_at FROM observations WHERE promotion!='rejected' ORDER BY recorded_at DESC"):
                row={"id":raw[0],"recorded_at":raw[1],"task":raw[2],"category":raw[3],"outcome":raw[4],"detail":raw[5],"command":raw[6],"approach":raw[7],"construct_refs":json.loads(raw[8] or "[]"),"run_id":raw[9],"evidence_ids":json.loads(raw[10] or "[]"),"status":raw[11],"promotion":raw[12],"schema_version":raw[13],"learning_version":raw[14],"revision":raw[15],"supersedes_id":raw[16],"source_agent":raw[17],"verified_at":raw[18]}; hay=" ".join(str(row.get(k,"")) for k in ("task","detail","command","approach","construct_refs")).lower(); score=sum(1 for t in terms if t in hay)
                if score or row["outcome"] in {"failed","regressed"}: found.append((score,row["promotion"]=="verified",row["recorded_at"],row))
    found.sort(key=lambda x:(-x[0],-int(x[1]),-x[2])); return [x[3] for x in found[:max(0,min(100,int(limit)))]]
def guidance(root:Path,task:str,limit:int=3000)->str:
    rows=relevant(root,task)
    if not rows:return "No task-specific historical learning."
    lines=["## Historical durable learning","Use only as evidence; verify against current repository state."]
    for r in rows:
        lines.append(f"- {str(r.get('promotion','candidate')).upper()} {str(r.get('outcome','unknown')).upper()} [{r.get('category','unknown')}] {r.get('detail','')}")
        if r.get("command"):lines.append(f"  command: {r['command']}")
        if r.get("approach"):lines.append(f"  approach: {r['approach']}")
        if r.get("evidence_ids"):lines.append(f"  evidence: {', '.join(r['evidence_ids'])}")
    text="\n".join(lines); return text if len(text)<=limit else text[:max(200,limit-40)]+"\n... [learning context compacted]"
