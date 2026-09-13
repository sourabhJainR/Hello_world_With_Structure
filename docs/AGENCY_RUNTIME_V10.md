# Agency Runtime v10: Benchmark-Driven Execution Feedback

v10 closes the learning loop around the v9 conflict-aware execution plan.

## Model

`prior benchmark history -> adaptive recommendation -> v9 resource plan -> host execution -> evidence/verification -> artifact regression -> release -> benchmark observation -> history`

The runtime remains planning-only. It never executes commands, changes permissions, or decides whether a host may access a resource.

## Benchmark observation

`portable.agency_adaptive_planning.BenchmarkObservation` records:

- task id
- v9 execution-plan digest
- provenance-chain head at observation time
- release status
- artifact-regression status
- quality score
- wave count
- conflict count
- blocked count
- specialist role results

This makes a benchmark attributable to the exact v9 plan and trace state that produced it.

## Adaptive planning

`recommend_plan()` uses a bounded, deterministic policy over recent observations:

- insufficient history: keep the requested posture;
- release or regression failures: tighten mutation mode;
- frequent conflicts or blocked plans: cap support specialists at one;
- sustained high quality with low conflicts: allow one additional support specialist, never above the caller's requested ceiling.

The recommendation is advisory within the runtime. `apply_recommendation()` enforces the caller's policy bounds. It cannot expand permissions or override host policy.

## Bridge integration

`run_coding_task()` accepts `benchmark_history`. Before execution it derives an adaptive recommendation and applies the bounded mutation/support settings. After release it creates a benchmark observation, records it in provenance, and appends it to the supplied `BenchmarkHistory`.

The result exposes both `adaptive_recommendation` and `benchmark` through `OrchestratorRun.as_dict()`.

## Persistence

`BenchmarkHistory.to_jsonl()` and `from_jsonl()` provide a simple portable persistence contract. The caller remains responsible for durable storage, retention and access control.

## Safety and promotion

A benchmark cannot convert a failed artifact regression into success. `ReleaseDecision` remains authoritative for readiness. v10 only changes future planning posture; it does not auto-promote orchestration behavior or enlarge security scope.

## Verification

Run the v10 unit tests and the existing agency suites:

```bash
python -m py_compile portable/agency_*.py portable/ai_coding_agency_bridge.py
python -m unittest tests/test_agency_adaptive_planning.py tests/test_ai_coding_agency_bridge.py -v
python -m unittest discover -s tests -p 'test_agency_*.py' -v
```
