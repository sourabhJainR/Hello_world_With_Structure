# Continuous AGI-Aligned Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continuously process every completed task into durable experience, benchmark history, empirically tuned strategy/calibration/iteration policies, and verified guidance for future tasks.

**Architecture:** Extend the existing `AdaptiveLearningStore` with append-only benchmark observations, durable policy versions, maintenance receipts, and evidence-gated tuning. Use the existing `AutomationScheduler` as the single durable maintenance trigger and keep `AdaptiveRuntime.run()` limited to recording outcomes and consuming already-approved guidance. Reuse existing cognitive learning, Dream Memory, continual-learning regression, and learning-controller semantics instead of creating parallel subsystems.

**Tech Stack:** Python, SQLite, existing `PersistentMemory`, `AutomationScheduler`, cognitive learning, Dream Memory, continual-learning guard, deterministic pytest harness, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-continuous-agi-learning-loop-design.md`

## Global Constraints

- Active task execution must never mutate learning policy synchronously.
- Raw learning and benchmark observations are append-only.
- Policy changes require evidence gates and holdout/transfer validation.
- Regressions preserve or restore the prior policy.
- Maintenance work is bounded per cycle and retryable.
- New guidance applies only to future task rounds.
- Existing safety, quality, verification, and architecture checks remain release gates.

---

### Task 1: Add append-only experience/benchmark history primitives

**Files:**
- Modify: `portable/adaptive_learning.py`
- Modify: `portable/__init__.py`
- Test: `tests/test_adaptive_learning.py` or the repository's existing adaptive-learning test module discovered during implementation

**Interfaces:**
- Consumes: `PersistentMemory`, `DeferredLearningJob`, existing cognitive-learning evidence.
- Produces: immutable benchmark/experience record types, append-only persistence, history queries, deterministic record digests.

- [ ] **Step 1: Write the failing tests**

Add tests asserting that recording a verified outcome appends a history record containing task/capability, strategy version, quality, confidence, iterations, evidence, round metadata, and transfer class; a second write does not overwrite the first; history ordering is deterministic.

```python
def test_benchmark_history_is_append_only(memory):
    store = AdaptiveLearningStore(memory, "project")
    first = store.record_benchmark(task_id="t1", capability="planning", strategy="s1",
                                   score=0.8, confidence=0.6, iterations=4,
                                   evidence=("e1",), verified=True, evaluation_class="baseline")
    second = store.record_benchmark(task_id="t2", capability="planning", strategy="s1",
                                    score=0.9, confidence=0.7, iterations=3,
                                    evidence=("e2",), verified=True, evaluation_class="holdout")
    assert first.record_id != second.record_id
    history = store.benchmark_history()
    assert [item.record_id for item in history] == [first.record_id, second.record_id]
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pytest tests/test_adaptive_learning.py::test_benchmark_history_is_append_only -q`
Expected: FAIL because the history interface does not yet exist.

- [ ] **Step 3: Implement the minimal history layer**

Add a frozen record type and SQLite table keyed by `(project, record_id)` with immutable inserts, indexes for capability/strategy/evaluation class/time, and bounded history retrieval. Include evidence ids and a digest over canonical serialized fields.

- [ ] **Step 4: Run focused tests and existing adaptive-learning tests**

Run: `pytest tests/test_adaptive_learning.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_learning.py portable/__init__.py tests/test_adaptive_learning.py
git commit -m "feat: add append-only adaptive benchmark history"
```

---

### Task 2: Build durable continuous maintenance scheduling

**Files:**
- Modify: `portable/adaptive_learning.py`
- Modify: `portable/adaptive_runtime.py`
- Modify: `portable/automation_scheduler.py` only if the existing scheduler needs a compatibility helper
- Test: adaptive-runtime/automation-scheduler tests

**Interfaces:**
- Consumes: `AutomationScheduler`, `AdaptiveLearningStore.process()`.
- Produces: `ensure_learning_maintenance()`, a bounded maintenance handler, and a durable maintenance receipt type/history.

- [ ] **Step 1: Write failing scheduler and maintenance tests**

Test idempotent registration, one claimed run, deferred-job processing, receipt persistence, bounded processing, retryable failure, and isolation from `AdaptiveRuntime.run()`.

```python
def test_learning_maintenance_is_idempotent(runtime, project_root):
    first = runtime.ensure_learning_maintenance(project_root, interval_seconds=60)
    second = runtime.ensure_learning_maintenance(project_root, interval_seconds=60)
    assert first.schedule_id == second.schedule_id
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_adaptive_runtime.py -k maintenance -q`
Expected: FAIL because maintenance registration/receipts are absent.

- [ ] **Step 3: Implement maintenance registration and bounded execution**

Create a deterministic schedule key derived from project identity. Register with `AutomationScheduler.add()` only when absent. Add a runtime method that claims due work, calls `store.process(limit=budget)`, invokes consolidation/tuning in bounded stages, records a receipt, and finishes with `success` or `retryable` as appropriate. Never execute it inside `run()`.

- [ ] **Step 4: Verify focused scheduler tests**

Run: `pytest tests/test_adaptive_runtime.py -k maintenance -q && pytest tests/test_automation_scheduler.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_learning.py portable/adaptive_runtime.py portable/automation_scheduler.py tests
git commit -m "feat: continuously schedule adaptive maintenance"
```

---

### Task 3: Add versioned adaptive policy and empirical tuner

**Files:**
- Create: `portable/adaptive_tuning.py`
- Modify: `portable/adaptive_learning.py`
- Modify: `portable/adaptive_runtime.py`
- Test: `tests/test_adaptive_tuning.py`

**Interfaces:**
- Consumes: benchmark history, current policy, existing `ContinualLearningGuard`/learning-controller concepts.
- Produces: `AdaptivePolicy`, `TuningDecision`, `AdaptiveTuner.evaluate()`, `AdaptiveTuner.promote()`, and current-policy lookup.

- [ ] **Step 1: Write failing tuner tests**

Cover repeated strategy improvement, no-change when evidence is insufficient, rollback on regression, capability-scoped promotion, and immutable policy versioning.

```python
def test_tuner_requires_repeated_independent_benefit(history, tuner):
    # two independent rounds improve score without regression
    tuner.record_round(...)
    tuner.record_round(...)
    decision = tuner.evaluate("planning")
    assert decision.action == "promote"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_adaptive_tuning.py -q`
Expected: FAIL because the tuner does not exist.

- [ ] **Step 3: Implement policy records and evidence gates**

Store immutable policy versions with parent version, scope, strategy id, confidence calibration parameters, iteration target, source evidence, creation round, and status. Require a minimum number of independent observations and a positive quality/cost tradeoff. Keep task-family policy scoped when evidence does not generalize.

- [ ] **Step 4: Integrate existing regression semantics**

Use the repository's continual-learning guard and strategy-learning concepts so promotion is shadow/holdout evaluated and negative deltas retain or restore the prior policy.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_adaptive_tuning.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add portable/adaptive_tuning.py portable/adaptive_learning.py portable/adaptive_runtime.py tests/test_adaptive_tuning.py
git commit -m "feat: empirically evolve adaptive strategy policies"
```

---

### Task 4: Add confidence calibration learning

**Files:**
- Modify: `portable/adaptive_tuning.py`
- Modify: `portable/adaptive_learning.py`
- Test: `tests/test_adaptive_tuning.py`

**Interfaces:**
- Consumes: historical confidence and realized verified outcomes.
- Produces: bounded calibration adjustment in `AdaptivePolicy` and calibration diagnostics in `TuningDecision`.

- [ ] **Step 1: Write failing calibration tests**

Cover systematic over-confidence, systematic under-confidence, insufficient history, capped adjustment, and holdout validation.

```python
def test_overconfidence_is_bounded_and_requires_history(tuner):
    for outcome in [False, False, True, False, False, True]:
        tuner.record_confidence(..., predicted=0.9, realized=outcome)
    result = tuner.calibrate(...)
    assert result.adjustment < 0
    assert abs(result.adjustment) <= 0.2
```

- [ ] **Step 2: Run focused test and verify failure**

Run: `pytest tests/test_adaptive_tuning.py -k confidence -q`
Expected: FAIL.

- [ ] **Step 3: Implement calibration estimator**

Compute a deterministic calibration error from verified observations, require the configured evidence floor, produce a bounded incremental adjustment, and validate the adjusted calibration on holdout history before promotion. Keep calibration independent from raw quality score.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_adaptive_tuning.py -k confidence -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_tuning.py portable/adaptive_learning.py tests/test_adaptive_tuning.py
git commit -m "feat: learn confidence calibration from history"
```

---

### Task 5: Add empirical iteration-reduction tuning and transfer validation

**Files:**
- Modify: `portable/adaptive_tuning.py`
- Modify: `portable/adaptive_learning.py`
- Test: `tests/test_adaptive_tuning.py`

**Interfaces:**
- Consumes: verified score/iterations history by task family and holdout/transfer classification.
- Produces: bounded iteration target recommendations with explicit reason/evidence.

- [ ] **Step 1: Write failing iteration tests**

```python
def test_iteration_target_reduces_only_when_quality_holds(tuner):
    # repeated independent observations: fewer iterations, same accepted quality
    ...
    decision = tuner.tune_iterations("planning")
    assert decision.new_iteration_target < decision.previous_iteration_target
```

Also test that a quality regression, verification failure, or insufficient independent rounds blocks reduction.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_adaptive_tuning.py -k iteration -q`
Expected: FAIL.

- [ ] **Step 3: Implement safe iteration tuner**

Calculate robust historical quality/iteration summaries, search only one bounded step below the current target, require holdout/transfer validation, and retain the previous target when the acceptance/evidence bar is not met. Never modify hard orchestration limits.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_adaptive_tuning.py -k iteration -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_tuning.py portable/adaptive_learning.py tests/test_adaptive_tuning.py
git commit -m "feat: tune iteration targets with transfer evidence"
```

---

### Task 6: Close the continual AGI loop in AdaptiveRuntime

**Files:**
- Modify: `portable/adaptive_runtime.py`
- Modify: `portable/__init__.py`
- Test: `tests/test_adaptive_runtime.py`, `tests/test_adaptive_learning.py`

**Interfaces:**
- Consumes: maintenance schedule, tuner, policy store.
- Produces: every-use learning cycle, current verified guidance, maintenance receipts, policy visibility for future runs.

- [ ] **Step 1: Write failing integration tests**

Verify that `run()` records a deferred outcome containing policy metadata, a due maintenance cycle processes it, the resulting verified guidance is visible to a later run, and the current task never sees a policy produced by itself.

- [ ] **Step 2: Run integration tests and verify failure**

Run: `pytest tests/test_adaptive_runtime.py -k "learning or maintenance" -q`
Expected: FAIL on missing policy/maintenance integration.

- [ ] **Step 3: Implement next-round-only policy application**

At run start, load the current verified policy snapshot and include it in guidance. At completion, record policy id alongside the outcome. Maintenance creates the next policy version only after the outcome is persisted and validated. Never mutate the active run's policy object.

- [ ] **Step 4: Add maintenance status/introspection**

Expose current policy and recent maintenance receipts for diagnostics without allowing callers to mutate persisted policy directly.

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/test_adaptive_runtime.py -k "learning or maintenance" -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add portable/adaptive_runtime.py portable/__init__.py tests
 git commit -m "feat: close the continual adaptive learning loop"
```

---

### Task 7: Full repository verification and PR hardening

**Files:**
- Modify: only files required by failures found during verification.
- Test: entire repository suite and required GitHub Actions checks.

- [ ] **Step 1: Run all targeted tests**

Run: `pytest tests/test_adaptive_learning.py tests/test_adaptive_tuning.py tests/test_adaptive_runtime.py tests/test_automation_scheduler.py -q`
Expected: PASS.

- [ ] **Step 2: Run the deterministic full suite**

Run: the repository's documented full deterministic test command from CI/readme.
Expected: PASS.

- [ ] **Step 3: Inspect every changed file for policy/safety regressions**

Verify no execution-path policy mutation, no unbounded maintenance loop, no non-deterministic benchmark ordering, and no bypass of verification gates.

- [ ] **Step 4: Create the PR**

Open the PR from `feat/continuous-agi-learning-loop` into `main` with the spec and plan linked in the body.

- [ ] **Step 5: Review the PR after implementation**

Inspect the complete diff and changed-file patches. Fix all material review findings before merging.

- [ ] **Step 6: Wait for and verify every required CI check**

Do not merge on a partial-green view. Confirm all repository-required workflows are green for the final PR head.

- [ ] **Step 7: Merge only after all checks are green**

Use the repository merge policy and expected final head SHA. Then verify the merge commit and `main` contents.

- [ ] **Step 8: Commit any post-review fixes and repeat verification**

If CI or review identifies a failure, fix it on the PR branch, re-run the full verification set, and re-check every workflow before merge.
