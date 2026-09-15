"""Bounded private working memory for one agent.

Private memory is disposable working state, not team knowledge. Writes are
serialized across threads/processes and old entries are evicted deterministically.
"""
from __future__ import annotations
import json,os,re,time
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterator
@contextmanager
def _lock(path:Path)->Iterator[None]:
    path.parent.mkdir(parents=True,exist_ok=True); h=path.open("a+")
    try:
        if os.name=="nt": import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_LOCK,1)
        else: import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_EX)
        yield
    finally:
        if os.name=="nt": import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_UNLCK,1)
        else: import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_UN)
        h.close()
class AgentMemory:
    """Bounded agent-private memory; never implicitly promoted to shared learning."""
    def __init__(self,root:Path,agent:str,*,run_id:str|None=None,max_entries:int=32,max_chars:int=12000)->None:
        if max_entries<1 or max_chars<1: raise ValueError("agent memory budgets must be positive")
        safe=re.sub(r"[^a-zA-Z0-9_.-]+","_",agent).strip("._") or "agent"; self.path=Path(root)/".ai-harness"/"agent-memory"/f"{safe}.jsonl"; self.lock_path=self.path.with_suffix(".lock"); self.run_id=run_id; self.max_entries=max_entries; self.max_chars=max_chars; self.path.parent.mkdir(parents=True,exist_ok=True)
    def _snapshot_unlocked(self)->list[dict[str,Any]]:
        if not self.path.exists(): return []
        rows=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(r,dict) and (self.run_id is None or r.get("run_id")==self.run_id): rows.append(r)
        return rows[-self.max_entries:]
    def snapshot(self):
        with _lock(self.lock_path): return self._snapshot_unlocked()
    def read(self,limit:int=5000)->str:
        text="\n".join(str(r.get("text","")).strip() for r in self.snapshot() if str(r.get("text","")).strip()); return text if len(text)<=limit else text[:max(200,limit-50)]+"\n...[agent memory compacted]"
    def remember(self,text:str,*,kind:str="note")->None:
        clean=str(text).strip()
        if not clean:return
        row={"schema_version":1,"kind":kind,"text":clean[:2000],"run_id":self.run_id,"recorded_at":int(time.time())}
        with _lock(self.lock_path):
            rows=self._snapshot_unlocked(); rows.append(row); rows=rows[-self.max_entries:]
            while rows and sum(len(json.dumps(x,ensure_ascii=False))+1 for x in rows)>self.max_chars: rows.pop(0)
            tmp=self.path.with_suffix(".tmp"); tmp.write_text("\n".join(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in rows)+("\n" if rows else ""),encoding="utf-8"); tmp.replace(self.path)
__all__=["AgentMemory"]
