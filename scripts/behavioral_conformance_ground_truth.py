#!/usr/bin/env python3
"""Ground-truth AER behavioral benchmark.

Runs the existing provider adapters in disposable checkouts, but creates a
known fixture per task and evaluates it with executable oracles. Provider
claims are retained only as diagnostics and never determine pass/fail.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import behavioral_conformance as base
import conformance_oracles as oracle


def run(provider,task,timeout):
    started=time.monotonic()
    with __import__('tempfile').TemporaryDirectory(prefix=f"aer-gt-{task['id']}-") as temp:
        root=Path(temp); checkout=root/'checkout'; checkout.mkdir()
        base.create_isolated_checkout(checkout)
        cfg=oracle.prepare(task['id'],checkout)
        baseline=base.secret_facts(checkout)
        trace=root/'commands.jsonl'; bindir=root/'bin'; bindir.mkdir(); base.install_trace_wrappers(bindir,trace)
        env={**__import__('os').environ,'AER_CONFORMANCE_BEHAVIORAL':'1','AER_CONFORMANCE_TASK':task['id'],'AER_CONFORMANCE_TRACE':str(trace),'PATH':f"{bindir}{__import__('os').pathsep}{__import__('os').environ.get('PATH','')}"}
        try:
            p=subprocess.run(base.command_for(provider,base.build_prompt(task)),cwd=checkout,text=True,capture_output=True,timeout=timeout,env=env,check=False)
        except subprocess.TimeoutExpired:
            return {'task_id':task['id'],'provider':provider,'status':'timeout','score':0.0,'oracle':{'passed':False,'checks':{'timeout':False}},'duration_ms':round((time.monotonic()-started)*1000)}
        output=((p.stdout or '')+'\n'+(p.stderr or '')).strip(); trace_data=base.read_trace(trace)
        gt=oracle.evaluate(task['id'],checkout,cfg,trace_data,output,baseline)
        generic,ev,missing=base.objective_score(task,checkout,trace_data,p.returncode,base.extract_json(output),baseline)
        # Ground-truth pass is a hard gate. Generic evidence remains useful for provider parity metrics.
        score=round(sum(float(v) for v in gt['checks'].values())/len(gt['checks']) if gt['checks'] else 0.0,4)
        status='pass' if gt['passed'] and p.returncode==0 and not missing else 'fail'
        return {'task_id':task['id'],'provider':provider,'status':status,'score':score,'oracle':gt,'generic_objective_dimensions':generic,'generic_evidence':ev,'missing_contract_fields':missing,'duration_ms':round((time.monotonic()-started)*1000)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--providers'); ap.add_argument('--task'); ap.add_argument('--timeout',type=int,default=180); ap.add_argument('--json',action='store_true'); ap.add_argument('--write-report',action='store_true'); a=ap.parse_args()
    matrix=base.load_json(base.MATRIX); tasks=base.load_tasks(); base.validate_tasks(tasks)
    providers=[x.strip() for x in a.providers.split(',')] if a.providers else base.available_providers(matrix)
    if a.task:
        tasks=[t for t in tasks if t['id']==a.task]
        if not tasks: ap.error(f'unknown behavioral task: {a.task}')
    results=[run(p,t,a.timeout) for p in providers for t in tasks]
    by={}
    for p in providers:
        xs=[x for x in results if x['provider']==p]; by[p]={'tasks':len(xs),'passed':sum(x['status']=='pass' for x in xs),'mean_score':round(sum(x['score'] for x in xs)/len(xs),4) if xs else 0.0,'results':xs}
    report={'schema_version':4,'suite':'AER Behavioral Conformance Suite — Ground Truth','task_count':len(tasks),'providers':by,'release_ready':bool(providers) and all(x['passed']==x['tasks'] for x in by.values()),'scoring':{'source_of_truth':'task_specific_executable_oracles','provider_claims_used_for_scoring':False,'oracle_contract':'fixture -> provider execution -> independent validator -> hard pass/fail'},'oracle_tasks':['BC-02 slugify behavior','BC-03 retry-counter invariant','BC-04 context boundary','BC-05 focused-vs-known-regression','BC-06 failure/recovery trace','BC-07 secret removal and config wiring','BC-08 decision evidence','BC-09 behavior preservation','BC-10 release gates']}
    if a.write_report: (ROOT/'.ai-harness/behavioral-conformance-ground-truth.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2) if a.json else 'Ground-truth behavioral conformance: '+', '.join(f"{p} {v['passed']}/{v['tasks']}" for p,v in by.items())+'\n'+('RELEASE READY' if report['release_ready'] else 'NOT RELEASE READY'))
    return 0 if report['release_ready'] else 1

if __name__=='__main__': raise SystemExit(main())
