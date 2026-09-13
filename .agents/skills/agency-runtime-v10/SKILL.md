---
name: agency-runtime-v10
description: Benchmark-driven feedback and adaptive planning layered on Agency Runtime v9.
---

# Agency Runtime v10

## Purpose
Turn completed v9 executions into deterministic benchmark observations that influence the next plan without weakening host security or promotion controls.

## Feedback loop
Use:
`PROFILE -> ADAPT FROM HISTORY -> ROUTE -> RESOURCE PLAN -> EXECUTE (HOST) -> EVIDENCE -> VERIFY -> REGRESSION -> RELEASE -> BENCHMARK -> PERSIST`

Each benchmark observation binds:
`TASK_ID | V9_PLAN_DIGEST | PROVENANCE_HEAD | RELEASE_STATUS | REGRESSION_STATUS | QUALITY_SCORE | WAVE_COUNT | CONFLICT_COUNT | BLOCKED_COUNT | SPECIALIST_RESULTS`.

## Adaptive rules
`portable.agency_adaptive_planning.recommend_plan` consumes prior observations before the next execution.

- Fewer than the minimum samples preserves the requested posture.
- Recent release or artifact-regression failures tighten mutation mode.
- Frequent resource conflicts or blocked work caps supporting specialists.
- Sustained high quality with low conflict may permit one additional support specialist, subject to the caller's requested ceiling.
- Recommendations never grant permissions, alter protected paths, bypass v9 scheduling, or make an unverified promotion decision.

## Benchmark persistence
`BenchmarkHistory.to_jsonl()` / `from_jsonl()` provide a portable history format. The caller owns durable storage policy; corrupted history must fail closed rather than being silently ignored.

## Provenance and regression
The v9 execution-plan digest remains the identity anchor for a run. The provenance head captured at benchmark time provides traceability to the decision chain. Artifact regression status is an explicit learning signal; a failed regression is never treated as a successful benchmark outcome.

## Host boundary
The runtime plans and learns; the host executes tools, controls credentials and permissions, enforces sandboxing, owns concurrency/side effects, and decides where benchmark history is persisted. v10 must not autonomously expand authority.

## Verification
At minimum run:
`python -m py_compile portable/agency_*.py portable/ai_coding_agency_bridge.py`
`python -m unittest tests/test_agency_adaptive_planning.py tests/test_ai_coding_agency_bridge.py -v`
`python -m unittest discover -s tests -p 'test_agency_*.py' -v`
