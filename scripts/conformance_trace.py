#!/usr/bin/env python3
"""Benchmark-only command tracing with deterministic one-shot verification failure injection."""
from __future__ import annotations
import json, os, shutil
from pathlib import Path

COMMANDS=("git","pytest","python","python3","dotnet","npm","node","go","cargo","mvn","gradle","rg","grep","find","cat","sed","awk","ls","head","tail","make")

def install(bin_dir:Path, trace:Path, inject_task:str|None=None)->None:
    original=os.environ.get("PATH",""); state=bin_dir/"failure-injection.state"
    for command in COMMANDS:
        real=shutil.which(command,path=original)
        if not real: continue
        script=f'''#!/usr/bin/env python3
import json, os, subprocess, sys, time, uuid
real={real!r}; trace={str(trace)!r}; state={str(state)!r}; task={inject_task!r}
name=sys.argv[0].rsplit('/',1)[-1]; invocation=uuid.uuid4().hex
with open(trace,'a',encoding='utf-8') as f:f.write(json.dumps({{"event":"command_start","invocation_id":invocation,"command":name,"args":sys.argv[1:],"cwd":os.getcwd(),"started":time.time()}})+'\\n')
if task=='BC-06' and name in {{'pytest','python','python3'}} and not os.path.exists(state):
    open(state,'w').close()
    with open(trace,'a',encoding='utf-8') as f:f.write(json.dumps({{"event":"failure_injected","invocation_id":invocation,"command":name,"returncode":97,"injected":True,"ended":time.time()}})+'\\n')
    raise SystemExit(97)
rc=subprocess.call([real,*sys.argv[1:]])
with open(trace,'a',encoding='utf-8') as f:f.write(json.dumps({{"event":"command_end","invocation_id":invocation,"command":name,"returncode":rc,"injected":False,"ended":time.time()}})+'\\n')
raise SystemExit(rc)
'''
        p=bin_dir/command; p.write_text(script,encoding="utf-8"); p.chmod(0o755)
