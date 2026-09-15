#!/usr/bin/env python3
"""Dependency-aware multi-agent execution with bounded context handoffs."""
from __future__ import annotations
import hashlib,json,os,threading,time
from contextlib import contextmanager
from dataclasses import dataclass,field
from pathlib import Path
from typing import Any,Callable,Iterator,Mapping
from portable.agency_state_graph import CheckpointStore,StateGraph
from portable.agent_memory import AgentMemory
from portable.context_engine import ContextEngine,ContextPolicy,handoff_from_output
from portable.learning_steward import LearningSteward
from portable.task_planner import Task,TaskPlan
from runtime.task_memory import guidance

@contextmanager
def _file_lock(path:Path)->Iterator[None]:
    path.parent.mkdir(parents=True,exist_ok=True); h=path.open("a+")
    try:
        if os.name=="nt":
            import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_EX)
        yield
    finally:
        if os.name=="nt":
            import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_UN)
        h.close()

@dataclass(frozen=True)
class AgentSpec:
    name:str; role:str; depends_on:tuple[str,...]=(); read_only:bool=True; critical:bool=True; focus:str=""
@dataclass
class AgentResult:
    name:str; role:str; status:str; attempts:int=1; exit_code:int=0; duration_seconds:float=0.0; output:str=""; error:str|None=None; memory_ids:list[str]=field(default_factory=list)

class SharedTaskMemory:
    """Run-scoped working memory with hard entry/size limits and cross-process writes."""
    def __init__(self,path:Path,intent_digest:str,*,max_entries:int=256,max_chars:int=200_000,context_policy:ContextPolicy|None=None)->None:
        if max_entries<1 or max_chars<1: raise ValueError("memory budgets must be positive")
        self.path=Path(path); self.intent_digest=intent_digest; self.max_entries=max_entries; self.max_chars=max_chars
        self.context=ContextEngine(context_policy); self._lock=threading.RLock(); self._process_lock=self.path.with_suffix(self.path.suffix+".lock")
        self.path.parent.mkdir(parents=True,exist_ok=True)
    @property
    def project_root(self)->Path: return self.path.parent.parent
    @staticmethod
    def _size(rows): return sum(len(json.dumps(r,ensure_ascii=False,sort_keys=True))+1 for r in rows)
    def publish(self,*,agent,role,kind,text,evidence=None,confidence=0.0)->str:
        clean=str(text).strip()
        if not clean: raise ValueError("shared memory text is required")
        payload={"schema_version":1,"intent_digest":self.intent_digest,"agent":agent,"role":role,"kind":kind,"text":clean,
                 "evidence":sorted(set(evidence or [])),"confidence":max(0.0,min(1.0,float(confidence))),"created_at":time.time()}
        payload["id"]=hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()[:20]
        with self._lock,_file_lock(self._process_lock):
            rows=self.snapshot(self.max_entries); rows.append(payload); rows=rows[-self.max_entries:]
            while rows and self._size(rows)>self.max_chars: rows.pop(0)
            if not rows: raise ValueError("shared memory item exceeds the hard memory budget")
            tmp=self.path.with_suffix(self.path.suffix+".tmp")
            tmp.write_text("\n".join(json.dumps(r,ensure_ascii=False,sort_keys=True) for r in rows)+"\n",encoding="utf-8"); tmp.replace(self.path)
        return payload["id"]
    def snapshot(self,limit=24):
        if limit<1 or not self.path.exists(): return []
        rows=[]
        with self.path.open(encoding="utf-8") as h:
            for line in h:
                try:r=json.loads(line)
                except json.JSONDecodeError:continue
                if isinstance(r,dict) and r.get("intent_digest")==self.intent_digest: rows.append(r)
        return rows[-int(limit):]
    def compact_text(self,*,relevant_agents=None,limit=None):
        rows=self.snapshot(self.max_entries)
        if relevant_agents is not None: rows=[r for r in rows if str(r.get("agent","")) in relevant_agents]
        packed=self.context.pack(self.context.from_memory(rows))
        if limit and len(packed)>limit: return packed[:max(200,limit-40)]+"\n...[context compacted]"
        return packed

def _private_memory(output):
    active=False; lines=[]
    for raw in str(output).splitlines():
        line=raw.strip()
        if line.lower().startswith("## private memory"): active=True; continue
        if active and line.startswith("## "): break
        if active and line: lines.append(line)
    return "\n".join(lines).strip()

class GraphAgentTeam:
    def __init__(self,agents:list[AgentSpec],*,max_parallel_read_only=4,max_agents=12,context_policy=None):
        self.agents={a.name:a for a in agents}
        if not self.agents: raise ValueError("graph agent team requires at least one agent")
        if len(self.agents)>max_agents: raise ValueError("graph agent team exceeds agent budget")
        self.max_parallel_read_only=max(1,int(max_parallel_read_only)); self.context_policy=context_policy or ContextPolicy(); self._plan=self._build_task_plan()
    def _build_task_plan(self):
        return TaskPlan([Task(id=a.name,title=a.role,description=a.focus,dependencies=list(a.depends_on),tags=["graph-agent"],acceptance=["agent execution completes successfully"],metadata={"read_only":a.read_only,"critical":a.critical}) for a in self.agents.values()])
    def _validate(self): self._plan.validate()
    def levels(self):
        plan=self._build_task_plan(); levels=[]
        while True:
            ready=plan.ready(tag="graph-agent")
            if not ready:
                if any(t.status=="pending" for t in plan.tasks.values()): raise ValueError("agent graph could not be scheduled")
                return levels
            levels.append([self.agents[t.id] for t in ready])
            for t in ready:t.status="done"
    def digest(self):
        payload=[{"name":a.name,"role":a.role,"depends_on":list(a.depends_on),"read_only":a.read_only,"critical":a.critical,"focus":a.focus} for level in self.levels() for a in level]
        return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    def _build_execution_graph(self,results,*,task,intent_digest,base_prompt,memory,invoke_agent):
        graph=StateGraph()
        for agent in self.agents.values():
            def run(state,agent=agent):
                deps=[state.get(f"result:{n}") for n in agent.depends_on]
                if any(not x or x.get("status")!="passed" for x in deps): return {f"result:{agent.name}":{"status":"blocked","activated":False}}
                relevant=set(agent.depends_on); relevant.add("planner")
                shared_context=memory.compact_text(relevant_agents=relevant)
                historical=guidance(memory.project_root,task,limit=2400)
                private=AgentMemory(memory.project_root,agent.name,run_id=intent_digest).read(limit=2200)
                focus=LearningSteward(memory.project_root,run_id=intent_digest,task=task).prompt() if agent.name=="learning-steward" else ""
                prompt=f'''# AER graph agent

You are the {agent.role} agent in a shared-memory engineering team.

## Task contract
{task}

Intent digest: {intent_digest}
Agent: {agent.name}
Role: {agent.role}
Focus: {agent.focus or "Use the task contract and repository evidence to perform your role."}
Read-only: {agent.read_only}

## Selected context
{shared_context}

## Reusable lessons from earlier runs
{historical}

## Your private session memory
{private or "No private memory yet."}

## Memory guardrails
- Execution agents focus on execution; they do not curate team learning.
- Private memory is optional, bounded, run-scoped working state and is never automatically promoted.
- Only the learning steward may create durable team learning.
- Durable learning is evidence-backed, versioned and append-only; verify it against current repository state.
- Do not copy the full transcript, logs or speculative reasoning into memory.
- Do not repeat completed dependency work unless verification requires it.

## Handoff rules
- Treat the task contract as authoritative.
- Verify inherited claims when important.
- Return concise findings, decisions, evidence, unresolved risks and the next action.
- {"Do not modify files." if agent.read_only else "You may modify files only within the task scope."}

{focus}

## Base instructions
{base_prompt}
'''
                code,output,duration=invoke_agent(agent,prompt)
                note=_private_memory(output)
                if note: AgentMemory(memory.project_root,agent.name,run_id=intent_digest).remember(note)
                result=AgentResult(agent.name,agent.role,"passed" if code==0 else "failed",exit_code=code,duration_seconds=duration,output=output)
                handoff=handoff_from_output(task_id=intent_digest,sender=agent.name,receiver="downstream",objective=agent.focus or task,output=output,success=code==0,max_chars=memory.context.policy.output_chars)
                result.memory_ids.append(memory.publish(agent=agent.name,role=agent.role,kind="handoff",text=handoff.render(memory.context.policy.output_chars),evidence=[f"agent:{agent.name}"],confidence=.8 if code==0 else .2))
                if agent.name=="learning-steward": LearningSteward(memory.project_root,run_id=intent_digest,task=task).persist(output,evidence_ids=[f"agent:{n}" for n in self.agents if n!=agent.name])
                results[agent.name]=result; payload=result.__dict__.copy(); payload["activated"]=True
                return {f"result:{agent.name}":payload}
            graph.add_node(agent.name,run)
        for name in [a.name for a in self.agents.values() if not a.depends_on]: graph.add_edge(StateGraph.START,name)
        for agent in self.agents.values():
            for dep in agent.depends_on: graph.add_edge(dep,agent.name)
        for name in [a.name for a in self.agents.values() if not any(a.name in x.depends_on for x in self.agents.values())]: graph.add_edge(name,StateGraph.END)
        return graph
    def execute(self,*,task,intent_digest,base_prompt,memory,invoke_agent,checkpoint=None,resume=False,run_id="graph-agent-team",max_steps=100):
        self._validate(); results={}
        run=self._build_execution_graph(results,task=task,intent_digest=intent_digest,base_prompt=base_prompt,memory=memory,invoke_agent=invoke_agent).compile().invoke({},run_id=run_id,checkpoint=checkpoint,resume=resume,max_steps=max_steps,parallel_nodes=lambda n:self.agents[n].read_only,max_parallel_nodes=self.max_parallel_read_only)
        for agent in self.agents.values():
            payload=run.state.get(f"result:{agent.name}")
            if isinstance(payload,dict) and payload.get("activated"): results[agent.name]=AgentResult(**{k:v for k,v in payload.items() if k!="activated"})
        critical=[run.state.get(f"result:{a.name}") for a in self.agents.values() if a.critical]
        return {"graph_digest":self.digest(),"intent_digest":intent_digest,"agents":{n:r.__dict__ for n,r in results.items()},"shared_memory_file":str(memory.path),"shared_memory_entries":len(memory.snapshot(500)),"accepted":all(isinstance(x,dict) and x.get("status")=="passed" for x in critical),"execution_trace":list(run.trace),"execution_digest":run.digest}

def team_for_route(route):
    mode=str(route.get("mode","implement")); caps=set(route.get("capabilities",[])); agents=[AgentSpec("planner","planner",focus="Turn the task contract into a small dependency-aware execution plan."),AgentSpec("explorer","explorer",depends_on=("planner",),focus="Trace relevant repository structure, callers, tests and protected behavior.")]
    if mode in {"research","poc"} or "research" in caps: agents.append(AgentSpec("researcher","researcher",depends_on=("planner",),focus="Gather only task-relevant technical evidence and alternatives."))
    if mode=="debug": agents.append(AgentSpec("rca","RCA investigator",depends_on=("planner","explorer"),focus="Establish root cause with evidence; do not patch."))
    if mode in {"implement","debug","poc"}:
        deps=["explorer"]
        if any(a.name=="researcher" for a in agents): deps.append("researcher")
        if mode=="debug": deps.append("rca")
        agents += [AgentSpec("builder","builder",depends_on=tuple(deps),read_only=False,focus="Implement the smallest safe task-scoped change."),AgentSpec("verifier","verifier",depends_on=("builder",),focus="Run or inspect deterministic verification and identify regressions.")]
        review_dep=("builder","verifier")
    else: review_dep=tuple(a.name for a in agents)
    agents.append(AgentSpec("correctness-reviewer","correctness reviewer",depends_on=review_dep,focus="Check correctness, compatibility, edge cases and test coverage."))
    if str(route.get("risk","low")) in {"high","critical"}: agents += [AgentSpec("security-reviewer","security reviewer",depends_on=review_dep,focus="Check trust boundaries, permissions, injection, secrets and unsafe defaults."),AgentSpec("architecture-reviewer","architecture reviewer",depends_on=review_dep,focus="Check coupling, dependency direction, maintainability and unnecessary complexity.")]
    agents.append(AgentSpec("synthesizer","team synthesizer",depends_on=tuple(a.name for a in agents if a.name.endswith("reviewer")),focus="Synthesize team evidence, unresolved risks and the recommended next action."))
    agents.append(AgentSpec("learning-steward","learning steward",depends_on=tuple(a.name for a in agents if a.name.endswith("reviewer") or a.name=="synthesizer"),read_only=True,critical=False,focus="Record only reusable, evidence-backed successes and failures for future runs."))
    return GraphAgentTeam(agents)
