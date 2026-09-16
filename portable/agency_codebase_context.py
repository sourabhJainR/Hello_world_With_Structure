"""Deterministic graph-aware codebase retrieval with bounded model context."""
from __future__ import annotations
from dataclasses import dataclass, field
import ast
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable, Sequence

DEFAULT_IGNORES = frozenset({".git",".hg",".svn",".venv","venv","node_modules","dist","build","__pycache__",".mypy_cache",".pytest_cache",".ruff_cache",".tox","coverage"})
TEXT_EXTENSIONS = frozenset({".py",".pyi",".js",".jsx",".ts",".tsx",".java",".cs",".go",".rs",".cpp",".cc",".h",".hpp",".c",".sql",".sh",".ps1",".md",".json",".yaml",".yml",".toml",".ini",".cfg",".xml",".txt",".proto"})
CONFIG_NAMES = frozenset({"pyproject.toml","package.json","package-lock.json","pnpm-lock.yaml","yarn.lock","go.mod","cargo.toml","pom.xml","build.gradle","build.gradle.kts","gradle.properties","appsettings.json","web.config","dockerfile","docker-compose.yml","docker-compose.yaml","makefile",".env.example","config.json"})
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")
DECL_RE = re.compile(r"\b(class|interface|struct|enum|function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(")
BASE_RE = re.compile(r"\b(?:extends|implements)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.I)
TEST_RE = re.compile(r"(^|[._/-])(test|tests|spec|specs)([._/-]|$)", re.I)

@dataclass(frozen=True)
class Symbol:
    name: str; kind: str; path: str; line: int

@dataclass(frozen=True)
class FileRecord:
    path: str; size: int; sha256: str; lines: int
    symbols: tuple[Symbol,...]=(); imports: tuple[str,...]=(); calls: tuple[str,...]=(); bases: tuple[str,...]=()

@dataclass(frozen=True)
class GraphEdge:
    source_path: str; target_path: str; kind: str; confidence: float; reason: str
    source_symbol: str=""; target_symbol: str=""

@dataclass(frozen=True)
class ContextChunk:
    path: str; start_line: int; end_line: int; text: str; score: float; reason: str
    @property
    def tokens(self)->int: return max(1,len(TOKEN_RE.findall(self.text)))

@dataclass(frozen=True)
class GraphTrace:
    seed_paths: tuple[str,...]; expanded_paths: tuple[str,...]; edges: tuple[GraphEdge,...]; stopped: tuple[str,...]
    def as_dict(self)->dict[str,object]:
        return {"seed_paths":list(self.seed_paths),"expanded_paths":list(self.expanded_paths),"stopped":list(self.stopped),"edges":[e.__dict__.copy() for e in self.edges]}

@dataclass(frozen=True)
class ContextReuseKey:
    snapshot_digest: str
    query: str
    token_budget: int
    max_files: int
    context_lines: int
    graph_hops: int

    def __post_init__(self) -> None:
        if not self.snapshot_digest or not self.query.strip():
            raise ValueError("snapshot_digest and query are required")
        if min(self.token_budget, self.max_files, self.context_lines) < 1 or self.graph_hops < 0:
            raise ValueError("context limits must be valid")

    def digest(self) -> str:
        payload = "|".join((self.snapshot_digest, self.query.strip(), str(self.token_budget), str(self.max_files), str(self.context_lines), str(self.graph_hops)))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

@dataclass(frozen=True)
class CodebaseContext:
    root: str; query: str; snapshot_digest: str; chunks: tuple[ContextChunk,...]
    relevant_paths: tuple[str,...]; unknowns: tuple[str,...]; token_estimate: int
    files_scanned: int; files_read: int
    graph_trace: GraphTrace=field(default_factory=lambda:GraphTrace((),(),(),()))
    context_version: str="1"
    retrieval_fingerprint: str=""

    def reuse_key(self, *, token_budget: int, max_files: int, context_lines: int, graph_hops: int) -> ContextReuseKey:
        return ContextReuseKey(self.snapshot_digest, self.query, token_budget, max_files, context_lines, graph_hops)

    @property
    def omitted_count(self) -> int:
        return sum(1 for path in self.unknowns if path.startswith("Relevant files omitted from context budget:"))

    def as_dict(self)->dict[str,object]:
        return {"root":self.root,"query":self.query,"snapshot_digest":self.snapshot_digest,"context_version":self.context_version,"retrieval_fingerprint":self.retrieval_fingerprint,"relevant_paths":list(self.relevant_paths),"unknowns":list(self.unknowns),"token_estimate":self.token_estimate,"files_scanned":self.files_scanned,"files_read":self.files_read,"graph_trace":self.graph_trace.as_dict(),"chunks":[c.__dict__|{"tokens":c.tokens} for c in self.chunks]}

@dataclass
class CodebaseIndex:
    root: Path; files: dict[str,FileRecord]=field(default_factory=dict); edges: tuple[GraphEdge,...]=()
    @classmethod
    def build(cls,root:str|Path,*,ignores:Iterable[str]=DEFAULT_IGNORES)->"CodebaseIndex":
        root_path=Path(root).resolve(); ignored=set(ignores); records={}
        for current,dirs,names in os.walk(root_path):
            dirs[:]=[d for d in dirs if d not in ignored]
            for name in names:
                path=Path(current)/name; rel=path.relative_to(root_path).as_posix()
                if path.is_symlink() or path.suffix.lower() not in TEXT_EXTENSIONS: continue
                try: data=path.read_bytes(); text=data.decode("utf-8")
                except (OSError,UnicodeDecodeError): continue
                symbols,imports,calls,bases=_extract_structure(rel,text)
                records[rel]=FileRecord(rel,len(data),hashlib.sha256(data).hexdigest(),text.count("\n")+bool(text),tuple(symbols),tuple(imports),tuple(calls),tuple(bases))
        index=cls(root_path,records); index.edges=tuple(_build_edges(index)); return index
    def digest(self)->str:
        payload="\n".join(f"{r.path}|{r.size}|{r.sha256}|{','.join(s.name for s in r.symbols)}|{','.join(r.imports)}|{','.join(r.calls)}|{','.join(r.bases)}" for r in sorted(self.files.values(),key=lambda x:x.path))
        return hashlib.sha256(payload.encode()).hexdigest()
    def neighbors(self,path:str,*,kinds:Sequence[str]=())->tuple[GraphEdge,...]:
        allowed=set(kinds); return tuple(e for e in self.edges if (e.source_path==path or e.target_path==path) and (not allowed or e.kind in allowed))

def _name(node:ast.AST)->str:
    if isinstance(node,ast.Name): return node.id
    if isinstance(node,ast.Attribute):
        left=_name(node.value); return f"{left}.{node.attr}" if left else node.attr
    return ""

def _extract_structure(path:str,text:str):
    symbols=[]; imports=[]; calls=[]; bases=[]
    if path.endswith((".py",".pyi")):
        try: tree=ast.parse(text)
        except SyntaxError: tree=None
        if tree:
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    symbols.append(Symbol(node.name,"class" if isinstance(node,ast.ClassDef) else "function",path,node.lineno))
                    if isinstance(node,ast.ClassDef): bases += [_name(x) for x in node.bases if _name(x)]
                elif isinstance(node,ast.Import): imports += [a.name for a in node.names]
                elif isinstance(node,ast.ImportFrom) and node.module: imports.append(node.module)
                elif isinstance(node,ast.Call):
                    n=_name(node.func)
                    if n: calls.append(n)
    else:
        for no,line in enumerate(text.splitlines(),1):
            m=DECL_RE.search(line)
            if m: symbols.append(Symbol(m.group(2),"interface" if m.group(1).lower()=="interface" else "class" if m.group(1).lower()=="class" else "function",path,no))
            if re.search(r"^\s*(?:import|using|require|from)\b",line): imports.append(line.strip())
            calls += [m.group(1) for m in CALL_RE.finditer(line)]
            bases += [m.group(1) for m in BASE_RE.finditer(line)]
    return symbols,imports,calls,bases

def _module_variants(value:str)->set[str]:
    value=re.sub(r"^(?:import|using|from|require)\s+","",value.strip().strip("\"'"),flags=re.I).split()[0] if value.strip() else ""
    return {value.replace("\\","/").replace(".","/").lstrip("/")}

def _resolve_import(index:CodebaseIndex,imported:str)->list[str]:
    variants=_module_variants(imported); out=[]
    for path in index.files:
        stem=Path(path).with_suffix("").as_posix()
        if any(stem==v or stem.endswith("/"+v) or Path(path).stem==v.split("/")[-1] for v in variants): out.append(path)
    return sorted(set(out))

def _build_edges(index:CodebaseIndex)->list[GraphEdge]:
    edges=[]; symbol_paths={}
    for r in index.files.values():
        for s in r.symbols: symbol_paths.setdefault(s.name.lower(),set()).add(r.path)
    configs={}
    for r in index.files.values():
        for imp in r.imports:
            for target in _resolve_import(index,imp)[:4]: edges.append(GraphEdge(r.path,target,"imports",.90,f"resolved-import:{imp}"))
        for base in r.bases:
            name=base.split(".")[-1].lower()
            for target in sorted(symbol_paths.get(name,())): edges.append(GraphEdge(r.path,target,"implements",.85,f"base-type:{base}",target_symbol=name))
        for call in r.calls:
            name=call.split(".")[-1].lower(); candidates=sorted(symbol_paths.get(name,()))
            if candidates:
                target=r.path if r.path in candidates else candidates[0]
                conf=.95 if target==r.path else .75 if len(candidates)==1 else .50
                edges.append(GraphEdge(r.path,target,"calls",conf,f"symbol-resolution:{call}",target_symbol=name))
        if Path(r.path).name.lower() in CONFIG_NAMES or ".github/" in r.path.lower():
            try: configs[r.path]=(index.root/r.path).read_text(encoding="utf-8",errors="ignore").lower()
            except OSError: pass
    tests=[p for p in index.files if TEST_RE.search(p)]
    for test in tests:
        r=index.files[test]; refs={x.split(".")[-1].lower() for x in r.calls+r.imports}
        for target,tr in index.files.items():
            if target==test or TEST_RE.search(target): continue
            if Path(target).stem.lower() in refs or any(s.name.lower() in refs for s in tr.symbols): edges.append(GraphEdge(test,target,"tests",.70,"test-name-or-symbol-reference"))
    for config,text in configs.items():
        for target in index.files:
            if target!=config and Path(target).stem.lower() in text: edges.append(GraphEdge(config,target,"configures",.65,"configuration-name-reference"))
    return list({(e.source_path,e.target_path,e.kind,e.source_symbol,e.target_symbol):e for e in edges}.values())

def _terms(query:str)->tuple[str,...]: return tuple(sorted({x.lower() for x in TOKEN_RE.findall(query) if len(x)>1},key=lambda x:(-len(x),x)))

def _rank_files(index:CodebaseIndex,query:str):
    terms=_terms(query); ranked=[]
    for r in index.files.values():
        p=r.path.lower(); sy=" ".join(s.name.lower() for s in r.symbols); im=" ".join(r.imports).lower(); score=0.; why=[]
        for t in terms:
            if t in p: score+=6.; why.append(f"path:{t}")
            if t in sy: score+=8.; why.append(f"symbol:{t}")
            if t in im: score+=2.; why.append(f"import:{t}")
        if Path(r.path).name.lower() in CONFIG_NAMES or TEST_RE.search(r.path): score+=.5
        if score: ranked.append((score,r,",".join(why[:5])))
    return sorted(ranked,key=lambda x:(-x[0],x[1].path))

def _expand_graph(index:CodebaseIndex,seeds:Sequence[str],hops:int):
    limit=max(0,min(2,hops)); seen=set(seeds); frontier=list(seeds); ranked=[]; edges=[]; stopped=[]
    for depth in range(1,limit+1):
        nxt=[]
        for path in frontier:
            for edge in index.neighbors(path):
                other=edge.target_path if edge.source_path==path else edge.source_path
                if other in seen: continue
                if edge.kind=="calls": relation,weight=("callee",5.) if edge.source_path==path else ("caller",4.5)
                elif edge.kind=="implements": relation,weight="interface-or-implementation",4.
                elif edge.kind=="tests": relation,weight="test",3.5
                elif edge.kind=="configures": relation,weight="configuration",3.
                else: relation,weight="dependency",3.
                ranked.append((other,weight*edge.confidence/depth,f"graph:{relation}:{edge.reason}")); edges.append(edge); seen.add(other); nxt.append(other)
        frontier=nxt
        if depth==limit and frontier: stopped.append("hop_budget_exhausted")
    if not edges and seeds: stopped.append("no_graph_successors")
    best={}
    for p,s,r in ranked:
        if p not in best or s>best[p][0]: best[p]=(s,r)
    expanded=sorted(((p,s,r) for p,(s,r) in best.items()),key=lambda x:(-x[1],x[0]))
    return expanded,GraphTrace(tuple(seeds),tuple(p for p,_,_ in expanded),tuple(edges),tuple(stopped))

def retrieve(index:CodebaseIndex,query:str,*,token_budget:int=4000,max_files:int=12,context_lines:int=20,graph_hops:int=2)->CodebaseContext:
    if token_budget<1 or max_files<1 or context_lines<1: raise ValueError("token_budget, max_files and context_lines must be positive")
    ranked=_rank_files(index,query); unknowns=[]
    if not ranked:
        trace=GraphTrace((),(),(),("no_seed_match",)); return CodebaseContext(str(index.root),query,index.digest(),(),(),("No indexed file path, symbol, or import matched the query",),0,len(index.files),0,trace,"1",ContextReuseKey(index.digest(),query,token_budget,max_files,context_lines,graph_hops).digest())
    seeds=[r.path for _,r,_ in ranked[:min(3,max_files)]]; graph_ranked,trace=_expand_graph(index,seeds,graph_hops)
    candidates={r.path:(s,why or "ranked-file") for s,r,why in ranked[:max_files]}
    for p,s,why in graph_ranked:
        if p not in candidates or s>candidates[p][0]: candidates[p]=(s,why)
    ordered=sorted(candidates.items(),key=lambda x:(-x[1][0],x[0]))[:max_files]; chunks=[]; used=0; files_read=0; terms=_terms(query)
    for p,(score,why) in ordered:
        try: text=(index.root/p).read_text(encoding="utf-8")
        except (OSError,UnicodeDecodeError): unknowns.append(f"Unable to read {p}"); continue
        files_read+=1; lines=text.splitlines(); hits=[i for i,line in enumerate(lines) if any(t in line.lower() for t in terms)] or [s.line-1 for s in index.files[p].symbols[:2]] or [0]
        selected=set()
        for hit in hits[:4]:
            start=max(0,hit-context_lines//2); selected.update(range(start,min(len(lines),start+context_lines)))
        if not selected: unknowns.append(f"No readable evidence window found in {p}"); continue
        start,end=min(selected),max(selected)+1; chunk=ContextChunk(p,start+1,end,"\n".join(lines[start:end]),score,why)
        if used+chunk.tokens>token_budget: continue
        chunks.append(chunk); used+=chunk.tokens
        if used>=token_budget: break
    omitted=[p for p,_ in ordered if p not in {c.path for c in chunks}]
    if omitted: unknowns.append("Relevant files omitted from context budget: "+", ".join(omitted))
    unknowns.extend("Graph retrieval stopped: "+x for x in trace.stopped)
    key=ContextReuseKey(index.digest(),query,token_budget,max_files,context_lines,graph_hops)
    return CodebaseContext(str(index.root),query,index.digest(),tuple(chunks),tuple(c.path for c in chunks),tuple(dict.fromkeys(unknowns)),used,len(index.files),files_read,trace,"1",key.digest())

def retrieve_from_path(root:str|Path,query:str,**kwargs:object)->CodebaseContext: return retrieve(CodebaseIndex.build(root),query,**kwargs)

__all__ = ["CodebaseContext", "CodebaseIndex", "ContextChunk", "ContextReuseKey", "FileRecord", "GraphEdge", "GraphTrace", "Symbol", "retrieve", "retrieve_from_path"]
