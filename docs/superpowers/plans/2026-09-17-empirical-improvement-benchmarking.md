# Empirical Improvement and Benchmarking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the integrated AER runtime empirically improve output quality over time while keeping execution workers focused and moving auxiliary learning, memory consolidation, compaction, and benchmarking off the active task path.

**Architecture:** Keep `DreamMemory` as the post-run consolidation boundary. Add a durable workstyle/quality profile, an asynchronous-style maintenance queue represented by persisted deferred jobs, and an empirical improvement harness that compares baseline versus candidate strategy outcomes using replayable benchmark cases. The worker only retrieves verified guidance before execution; it records compact outcome metrics after execution and does not perform consolidation or compaction itself. Promotion requires evidence and regression checks.

**Tech Stack:** Python 3, stdlib `dataclasses`/`sqlite3`/`json`/`hashlib`, existing `PersistentMemory`, `DreamMemory`, `DeepEvaluator`, `ContinualLearningGuard`, `AdaptiveRuntime`.

**Spec:** Approved chat design from 2026-09-17: worker lane stays task-focused; learning lane consolidates episodes, compacts memory, updates user/workstyle profile, evaluates quality and strategy candidates; verified learning is promoted only after regression/benchmark evidence.

## Global Constraints

- Dream Memory remains post-run and outside the execution graph.
- Auxiliary memory/learning/compaction work must not become worker execution authority.
- Learned guidance remains advisory until evidence-backed promotion gates pass.
- Existing public runtime APIs and safety boundaries remain compatible.
- All new production behavior is developed test-first and covered by deterministic tests.
- Benchmarking must be replayable and expose quality, retry/iteration, calibration, and regression metrics.

---

### Task 1: Deferred learning and workstyle profile

**Files:**
- Create: `portable/adaptive_learning.py`
- Modify: `portable/adaptive_runtime.py`
- Modify: `portable/__init__.py`
- Test: `tests/portable/test_adaptive_learning.py`

**Interfaces:**
- `WorkStyleProfile(project: str, preferred_detail: str, verification_emphasis: str, iteration_target: float, confidence: float, observations: int)`.
- `DeferredLearningJob(job_id: str, project: str, task_id: str, kind: str, payload: dict[str, object], status: str)`.
- `AdaptiveLearningStore(memory: PersistentMemory, project: str)` with `enqueue(...)`, `pending(limit=...)`, `complete(job_id)`, `profile()`, and `record_outcome(...)`.
- `AdaptiveRuntime.run(..., learning_context=...)` records a compact deferred outcome instead of doing consolidation synchronously.
- `AdaptiveRuntime.process_learning(...)` drains deferred jobs explicitly outside the worker path and invokes Dream Memory plus profile updates.

- [ ] **Step 1: Write failing tests** for durable workstyle observations, deferred-job creation, explicit draining, and worker-path isolation.
- [ ] **Step 2: Run `pytest tests/portable/test_adaptive_learning.py -q` and verify the failures are due to missing APIs/behavior.
- [ ] **Step 3: Implement the minimal SQLite-backed store and explicit maintenance method; preserve `DreamMemory` as the consolidation engine.
- [ ] **Step 4: Run the focused tests and the existing cognitive/adaptive runtime tests.
- [ ] **Step 5: Commit `feat: defer learning and adapt workstyle from outcomes`.

### Task 2: Empirical quality and iteration benchmark harness

**Files:**
- Create: `portable/empirical_improvement.py`
- Modify: `portable/__init__.py`
- Test: `tests/portable/test_empirical_improvement.py`

**Interfaces:**
- `ImprovementObservation(case_id: str, strategy: str, score: float, iterations: int, confidence: float, evidence: tuple[str, ...])`.
- `ImprovementReport(baseline_score, candidate_score, score_delta, baseline_iterations, candidate_iterations, iteration_delta, calibration_delta, accepted, reason, digest)`.
- `EmpiricalImprovement.evaluate(baseline, candidate, min_score_gain=0.01, max_iteration_increase=0)`.
- `EmpiricalImprovement.run(cases, baseline_strategy, candidate_strategy, evaluator)` returns a report and rejects regressions, missing evidence, and iteration increases beyond the configured bound.
- Benchmark output must be deterministic for identical case inputs.

- [ ] **Step 1: Write failing tests for measurable quality improvement, reduced/equal iterations, evidence requirements, regression rejection, and deterministic digesting.
- [ ] **Step 2: Run the focused tests and confirm expected failures.
- [ ] **Step 3: Implement the evaluator wrapper using existing `DeepEvaluator`/`ContinualLearningGuard` primitives without duplicating benchmark semantics.
- [ ] **Step 4: Run focused tests plus `tests/portable/test_deep_evaluation.py` and `tests/portable/test_continual_learning.py` where present.
- [ ] **Step 5: Commit `feat: add empirical improvement gate and metrics`.

### Task 3: Integrated learning loop and benchmark scenario

**Files:**
- Modify: `portable/adaptive_runtime.py`
- Create: `tests/portable/test_integrated_learning_benchmark.py`
- Create: `examples/empirical_improvement_demo.py`
- Modify: `README.md`

**Interfaces:**
- `AdaptiveRuntime.process_learning(project_root, limit=...) -> list[dict[str, object]]` performs bounded maintenance outside task execution.
- `AdaptiveRuntime.benchmark_improvement(project_root, cases, ...) -> ImprovementReport` runs replayable empirical comparison without mutating active execution authority.
- Benchmark scenario must exercise: prior result retrieval, workstyle adaptation, deferred learning, Dream Memory consolidation, quality score, iteration count, and confidence/regression gating.

- [ ] **Step 1: Write the failing integration test proving `run()` leaves maintenance pending and `process_learning()` performs consolidation/adaptation afterward.
- [ ] **Step 2: Run the integration test and verify it fails for the missing integrated loop.
- [ ] **Step 3: Add the bounded integration APIs and example scenario.
- [ ] **Step 4: Run targeted portable suites and the full repository test command defined by CI.
- [ ] **Step 5: Commit `feat: integrate empirical learning and benchmarking`.

### Task 4: PR review and CI gate

**Files:**
- No code changes unless review findings require them.

- [ ] Open a PR from `feat/empirical-improvement-benchmarking` into `main`.
- [ ] Review the full diff for correctness, concurrency/state isolation, determinism, backwards compatibility, and preservation of Dream Memory boundaries.
- [ ] Fix every blocking or material review finding in follow-up commits.
- [ ] Wait for every CI check on the PR, including all checks added by the merge ref, not only named AI-harness checks.
- [ ] Merge only when the complete check set is green.
- [ ] Verify the resulting `main` commit and final repository state.
