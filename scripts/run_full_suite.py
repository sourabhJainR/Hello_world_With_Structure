#!/usr/bin/env python3
"""Run the complete deterministic repository quality suite."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
COMMANDS=[
 [sys.executable,"-m","unittest","discover","-s","tests","-v"],
 [sys.executable,"scripts/run_evals.py","--json"],
 [sys.executable,"scripts/run_p0_evals.py"],
 [sys.executable,".ai-harness/run.py","eval"],
 [sys.executable,".ai-harness/project_profile.py"],
 [sys.executable,".ai-harness/extension_registry.py"],
 [sys.executable,".ai-harness/placement.py","ExampleService.py","ExampleConstants.py","ExampleHandler.py"],
 [sys.executable,".ai-harness/worktree.py","list"],
]
def main():
    failures=[]
    for command in COMMANDS:
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        print("$ "+" ".join(command))
        print(result.stdout)
        if result.stderr: print(result.stderr,file=sys.stderr)
        if result.returncode: failures.append(command)
    print({"commands":len(COMMANDS),"failed":len(failures),"release_ready":not failures})
    return 1 if failures else 0
if __name__=="__main__": raise SystemExit(main())
