# LLM Adaptive Trigger Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the LLM-chat AdaptiveRuntime trigger so durable work survives process crashes, remains isolated and priority-aware, exposes observable state, reuses one adapter per runtime, and is directly available as a provider-neutral chat capability.

**Architecture:** `TriggerRuntime` remains the single durable event substrate and gains lease-aware claims, kind-filtered selection, explicit priority ordering, and durable completion metadata. `AdaptiveTrigger` remains a thin chat adapter over the existing `AdaptiveRuntime.run()` path, while a small provider-neutral capability contract makes the trigger callable from Claude/plugin-style hosts without coupling core runtime semantics to a provider.

**Tech Stack:** Python 3.11+, SQLite/WAL, dataclasses, existing `AdaptiveRuntime`, `TriggerRuntime`, Claude plugin manifest/skills, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-llm-adaptive-trigger-hardening-design.md`

## Global Constraints

- Preserve `TriggerRuntime` as the only durable trigger/event substrate; do not add a second scheduler or memory store.
- Preserve existing retry/backoff semantics and completion ownership checks by `claim_id`.
- Adaptive chat events use only `low`, `normal`, and `high` priorities.
- `AdaptiveTrigger` must remain fire-and-forget by default and use the existing process-wide four-worker executor.
- Chat execution must invoke normal `AdaptiveRuntime.run()` and must not bypass verification, evidence, permissions, policy, or learning gates.
- The scheduled monthly maintenance service remains the scheduled maintenance lane; it must not become the owner of chat semantics.
- Existing interval schedules and migrated last-day-of-month scheduling must remain compatible.
- Do not store arbitrary Python execution results in SQLite; only bounded, JSON-safe execution metadata may be persisted.
- Tests must cover crash recovery, kind isolation, priority ordering, single-owner concurrency, status/outcome lookup, convenience API reuse, capability schema, exports, and maintenance compatibility.
- No claimed work may become permanently stranded solely because a process disappeared after acquiring a claim.

---

## File Map

- Modify `portable/trigger_runtime.py`: durable trigger schema, migration, lease-aware claim/recovery, kind/priority-aware due selection, durable status/outcome metadata.
- Modify `portable/adaptive_trigger.py`: use explicit TriggerRuntime priority/kind APIs, recoverable dispatch, durable status access, reusable runtime-bound adapter, safe background error recording.
- Modify `portable/adaptive_runtime.py`: own/reuse one lazy `AdaptiveTrigger` instance for convenience calls without circular import at module load time.
- Modify `portable/__init__.py`: export the new adaptive-trigger public API and durable trigger status types.
- Create `portable/chat_capability.py`: provider-neutral `adaptive_runtime.trigger` capability descriptor and invoker contract backed by `AdaptiveTrigger`.
- Modify `.claude-plugin/plugin.json`: register the provider-neutral chat capability through the existing plugin surface without embedding runtime logic in the manifest.
- Modify `skills/ai-coding-orchestrator/SKILL.md`: document the tool contract and when the chat capability may be used.
- Modify `docs/LLM_CHAT_TRIGGER.md`: correct crash-recovery/status semantics and document the capability schema and host integration boundary.
- Modify `tests/test_trigger_runtime.py` or the existing trigger-runtime test location: lease, recovery, priority, kind filtering, concurrent ownership, status metadata.
- Modify `tests/test_adaptive_trigger.py`: adapter lifecycle, status lookup, reusable convenience path, background failure observability, priority propagation.
- Create `tests/test_chat_capability.py`: stable provider-neutral schema and invocation contract.
- Modify package/API tests as needed to verify `portable` exports.

---

### Task 1: Make TriggerRuntime Claims Crash-Recoverable

**Files:**
- Modify: `portable/trigger_runtime.py`
- Test: `tests/test_trigger_runtime.py`

**Interfaces:**
- Extends `TriggerEvent` with `claimed_at`, `lease_until`, `priority`, `completed_at`, and bounded `outcome` metadata while keeping existing positional fields backward-compatible where practical.
- Extends `TriggerRuntime.__init__` with `claim_lease_seconds: int = 300`.
- `TriggerRuntime.claim(event_id: str, *, now: datetime | None = None) -> TriggerClaim | None` may reclaim an expired claim atomically.
- `TriggerRuntime.due(*, now=None, limit=20, kind: str | None = None) -> tuple[TriggerEvent, ...]` includes pending work and expired claimed work only when the caller explicitly requests the relevant kind.

- [ ] **Step 1: Write failing lease tests**

Add tests proving an event claimed at `t0` is not claimable again before lease expiry, becomes recoverable after `lease_until`, and that a recovered claim receives a new `claim_id` without incrementing attempts until that new claim succeeds.

```python
def test_expired_claim_is_recoverable_without_duplicate_attempt_increment(scheduler):
    runtime = TriggerRuntime(scheduler, claim_lease_seconds=60)
    created = datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)
    event = runtime.emit("adaptive_runtime", {"task": "x"}, not_before=created)
    first = runtime.claim(event.event_id, now=created)
    assert first is not None
    assert first.event.attempts == 1

    before_expiry = runtime.claim(event.event_id, now=created + timedelta(seconds=59))
    assert before_expiry is None

    recovered = runtime.claim(event.event_id, now=created + timedelta(seconds=61))
    assert recovered is not None
    assert recovered.claim_id != first.claim_id
    assert recovered.event.attempts == 2
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/test_trigger_runtime.py -k "expired_claim or lease" -v`
Expected: FAIL because the current schema has no lease fields and claimed events are never reclaimable.

- [ ] **Step 3: Add additive SQLite migration and lease columns**

Extend `trigger_events` with `claimed_at`, `lease_until`, `completed_at`, `priority`, and `outcome`. Detect each missing column via `PRAGMA table_info(trigger_events)` and add it with safe defaults so existing databases migrate in place.

- [ ] **Step 4: Implement atomic reclaim-before-claim**

Under `BEGIN IMMEDIATE`, treat `status='claimed' AND lease_until<=now` as reclaimable. Clear the stale claim and then atomically transition the row to `claimed` with a new claim ID and `attempts=attempts+1`. Do not allow a live lease to be stolen.

- [ ] **Step 5: Preserve ownership on completion**

Keep `claim_id` ownership checks and clear lease metadata on successful, retryable, failed, and cancelled completion. Record `completed_at` only for terminal states.

- [ ] **Step 6: Run focused tests again**

Run: `pytest tests/test_trigger_runtime.py -k "expired_claim or lease" -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add portable/trigger_runtime.py tests/test_trigger_runtime.py
git commit -m "fix: recover expired trigger claims"
```

---

### Task 2: Add Kind Isolation and Functional Priority Ordering

**Files:**
- Modify: `portable/trigger_runtime.py`
- Test: `tests/test_trigger_runtime.py`

**Interfaces:**
- `TriggerRuntime.emit(..., priority: int = 1)` stores a normalized numeric priority; `0=high`, `1=normal`, `2=low`.
- `TriggerRuntime.due(..., kind=None)` filters by exact kind when provided.
- Due ordering is `priority ASC, available_at ASC, event_id ASC`.

- [ ] **Step 1: Write failing priority/isolation tests**

```python
def test_due_filters_kind_and_orders_by_priority(scheduler):
    runtime = TriggerRuntime(scheduler)
    high = runtime.emit("adaptive_runtime", {"task": "high"}, priority=0)
    low = runtime.emit("adaptive_runtime", {"task": "low"}, priority=2)
    unrelated = runtime.emit("other", {"task": "other"}, priority=0)

    due = runtime.due(kind="adaptive_runtime", limit=10)
    assert [event.event_id for event in due] == [high.event_id, low.event_id]
    assert unrelated.event_id not in [event.event_id for event in due]
```

- [ ] **Step 2: Run focused test and verify failure**

Run: `pytest tests/test_trigger_runtime.py -k "priority or kind" -v`
Expected: FAIL because `due()` currently sees all kinds and sorts only by availability/event ID.

- [ ] **Step 3: Implement normalized priority persistence and indexed ordering**

Add a numeric priority column, validate it is one of `0`, `1`, or `2`, update the due index to begin with `(status, priority, available_at, event_id)`, and include exact-kind filtering in SQL rather than filtering in Python after selection.

- [ ] **Step 4: Keep legacy interval callers compatible**

When generic `TriggerRuntime.emit()` is called without priority, default to normal priority. Preserve the existing payload format so old callers continue to read their event data.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_trigger_runtime.py -k "priority or kind" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add portable/trigger_runtime.py tests/test_trigger_runtime.py
git commit -m "feat: isolate and prioritize trigger dispatch"
```

---

### Task 3: Add Durable Trigger Status and Outcome Metadata

**Files:**
- Modify: `portable/trigger_runtime.py`
- Test: `tests/test_trigger_runtime.py`

**Interfaces:**
- Add `TriggerStatus` dataclass containing `event_id`, `kind`, `status`, `attempts`, `max_attempts`, `priority`, `available_at`, `claimed_at`, `lease_until`, `completed_at`, `last_detail`, and `outcome`.
- Add `TriggerRuntime.get(event_id: str) -> TriggerStatus | None`.
- Extend `complete(..., outcome: Mapping[str, Any] | None = None, ...)` with JSON-safe bounded serialization.

- [ ] **Step 1: Write failing status/outcome test**

```python
def test_status_and_outcome_are_durable(scheduler):
    runtime = TriggerRuntime(scheduler)
    event = runtime.emit("adaptive_runtime", {"task": "x"}, priority=0)
    claim = runtime.claim(event.event_id)
    assert claim is not None
    runtime.complete(
        event.event_id,
        claim.claim_id,
        "success",
        outcome={"result_status": "accepted"},
    )
    status = runtime.get(event.event_id)
    assert status is not None
    assert status.status == "success"
    assert status.outcome["result_status"] == "accepted"
    assert status.completed_at is not None
```

- [ ] **Step 2: Run focused test and verify failure**

Run: `pytest tests/test_trigger_runtime.py -k "status_and_outcome" -v`
Expected: FAIL because no status lookup or durable outcome exists.

- [ ] **Step 3: Implement status projection and bounded outcome serialization**

Persist only JSON-compatible mappings, truncate serialized outcome/detail to a bounded size, and expose a read-only status dataclass so callers never need to inspect SQLite directly.

- [ ] **Step 4: Preserve retry semantics**

Retryable completion keeps the event pending with updated `available_at`, preserves attempts, clears claim metadata, and records diagnostic detail. Terminal completion stores `completed_at` and the compact outcome.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/test_trigger_runtime.py -k "status_and_outcome" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add portable/trigger_runtime.py tests/test_trigger_runtime.py
git commit -m "feat: expose durable trigger status"
```

---

### Task 4: Harden AdaptiveTrigger Dispatch and Adapter Lifecycle

**Files:**
- Modify: `portable/adaptive_trigger.py`
- Modify: `portable/adaptive_runtime.py`
- Test: `tests/test_adaptive_trigger.py`

**Interfaces:**
- `AdaptiveTrigger.get_status(trigger_id: str) -> TriggerStatus | None` delegates to `TriggerRuntime.get`.
- `AdaptiveRuntime.adaptive_trigger` (property) returns one lazily created `AdaptiveTrigger` bound to that runtime.
- `AdaptiveRuntime.trigger_adaptive_runtime(...) -> TriggerReceipt` delegates to the cached adapter.
- `AdaptiveTrigger.dispatch_once(limit=20)` requests only `kind="adaptive_runtime"` events.

- [ ] **Step 1: Write failing lifecycle/isolation/status tests**

```python
def test_dispatch_once_ignores_unrelated_trigger_kinds(runtime):
    trigger = AdaptiveTrigger.for_runtime(runtime)
    runtime.trigger_runtime.emit("other", {"task": "leave me alone"})
    receipt = trigger.trigger_adaptive_runtime("run me", runtime.project_root, fire_and_forget=False)

    outcomes = trigger.dispatch_once(limit=20)
    assert [item.trigger_id for item in outcomes] == [receipt.trigger_id]
    assert runtime.trigger_runtime.get(receipt.trigger_id).status == "success"
    assert runtime.trigger_runtime.get("missing") is None


def test_runtime_reuses_one_adaptive_trigger(runtime):
    first = runtime.adaptive_trigger
    second = runtime.adaptive_trigger
    assert first is second
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_adaptive_trigger.py -k "ignores_unrelated or reuses_one" -v`
Expected: FAIL because dispatch has no kind filter and `AdaptiveRuntime` does not own a reusable adapter.

- [ ] **Step 3: Route dispatch through kind-filtered TriggerRuntime selection**

Change `dispatch_once()` to call `due(kind="adaptive_runtime")`. Keep exact event-ID claim semantics so one dispatcher cannot accidentally process a different event.

- [ ] **Step 4: Add status access and durable background completion metadata**

After a successful runner result, persist a small JSON-safe outcome such as `{"result_status": str(result.status)}` when available; otherwise persist `{"result_type": type(result).__name__}`. On exceptions, persist bounded diagnostic detail through `complete(..., "retryable", ...)` and leave the event recoverable.

- [ ] **Step 5: Add one lazy adapter per runtime**

Implement a private runtime field initialized under the existing runtime lock or a dedicated one-shot guard. Import `AdaptiveTrigger` inside the accessor to avoid module-load circular imports.

- [ ] **Step 6: Make the module-level convenience function reuse the runtime-owned adapter**

Replace `AdaptiveTrigger.for_runtime(runtime)` in the convenience helper with `runtime.adaptive_trigger` so repeated chat calls share the same adapter and synchronization boundary.

- [ ] **Step 7: Run focused tests**

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: PASS, including all pre-existing trigger tests plus the new lifecycle/status cases.

- [ ] **Step 8: Commit**

```bash
git add portable/adaptive_trigger.py portable/adaptive_runtime.py tests/test_adaptive_trigger.py
git commit -m "fix: harden adaptive chat trigger lifecycle"
```

---

### Task 5: Expose the Stable Public Package API

**Files:**
- Modify: `portable/__init__.py`
- Modify: `tests/test_adaptive_trigger.py`

**Interfaces:**
- `portable` exports `AdaptiveTrigger`, `AdaptiveTriggerRequest`, `TriggerOutcome`, `TriggerReceipt`, `TriggerStatus`, and `trigger_adaptive_runtime`.

- [ ] **Step 1: Write the public-import regression test**

```python
def test_adaptive_trigger_api_is_exported_from_portable():
    from portable import (
        AdaptiveTrigger,
        AdaptiveTriggerRequest,
        TriggerOutcome,
        TriggerReceipt,
        TriggerStatus,
        trigger_adaptive_runtime,
    )
    assert all(value is not None for value in (
        AdaptiveTrigger,
        AdaptiveTriggerRequest,
        TriggerOutcome,
        TriggerReceipt,
        TriggerStatus,
        trigger_adaptive_runtime,
    ))
```

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/test_adaptive_trigger.py -k "api_is_exported" -v`
Expected: FAIL because the current package `__init__` does not export the new API.

- [ ] **Step 3: Add imports and `__all__` entries**

Add only the new public trigger types; do not re-export internal executor or runner implementation details.

- [ ] **Step 4: Run focused test**

Run: `pytest tests/test_adaptive_trigger.py -k "api_is_exported" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add portable/__init__.py tests/test_adaptive_trigger.py
git commit -m "feat: export adaptive trigger public API"
```

---

### Task 6: Add Provider-Neutral Chat Capability Exposure

**Files:**
- Create: `portable/chat_capability.py`
- Modify: `.claude-plugin/plugin.json`
- Modify: `skills/ai-coding-orchestrator/SKILL.md`
- Create: `tests/test_chat_capability.py`

**Interfaces:**
- `AdaptiveRuntimeTriggerTool` exposes:
  - `name = "adaptive_runtime.trigger"`
  - `description` explaining immediate durable acceptance and non-blocking execution.
  - `input_schema() -> dict[str, Any]` returning JSON Schema with required `task` and `project_root`, optional `context`, `priority`, `event_id`, `max_attempts`.
  - `invoke(runtime, arguments) -> TriggerReceipt` delegating to the runtime-owned `AdaptiveTrigger`.
- The capability descriptor is provider-neutral; `.claude-plugin/plugin.json` references the capability surface but contains no runtime execution logic.

- [ ] **Step 1: Write schema and invocation tests**

```python
def test_adaptive_runtime_trigger_capability_schema():
    tool = AdaptiveRuntimeTriggerTool()
    schema = tool.input_schema()
    assert schema["type"] == "object"
    assert "task" in schema["required"]
    assert "project_root" in schema["required"]
    assert schema["properties"]["priority"]["enum"] == ["low", "normal", "high"]


def test_capability_invokes_durable_trigger(runtime):
    tool = AdaptiveRuntimeTriggerTool()
    receipt = tool.invoke(runtime, {
        "task": "test task",
        "project_root": str(runtime.project_root),
        "context": {"source": "chat"},
        "priority": "high",
        "max_attempts": 2,
    })
    assert receipt.status == "pending"
    assert runtime.trigger_runtime.get(receipt.trigger_id).priority == 0
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_chat_capability.py -v`
Expected: FAIL because the capability module does not yet exist.

- [ ] **Step 3: Implement the stable capability descriptor**

Keep validation in the capability layer limited to schema-level shape checks; leave business validation and persistence semantics in `AdaptiveTrigger`/`TriggerRuntime`. Return the same `TriggerReceipt` used by Python callers.

- [ ] **Step 4: Register the capability through the existing plugin surface**

Add a minimal manifest entry or capability reference matching the repository's existing plugin conventions. Do not add a second hook, subprocess, scheduler, or alternate execution engine.

- [ ] **Step 5: Document invocation semantics in the orchestrator skill**

State that the tool is for explicit requests to start an AdaptiveRuntime task, that it returns after durable persistence, and that callers should use `get_status()`/host-side status APIs for completion rather than waiting on a chat tool call.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_chat_capability.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add portable/chat_capability.py .claude-plugin/plugin.json skills/ai-coding-orchestrator/SKILL.md tests/test_chat_capability.py
git commit -m "feat: expose adaptive runtime chat capability"
```

---

### Task 7: Correct Chat Trigger Documentation and Maintenance-Service Boundary

**Files:**
- Modify: `docs/LLM_CHAT_TRIGGER.md`
- Modify: `portable/maintenance_service.py` only if a compatibility test demonstrates a needed non-breaking correction.
- Test: `tests/test_chat_capability.py` and relevant maintenance tests if present.

**Interfaces:**
- Documentation states that persisted events are recoverable only when a host constructs an `AdaptiveTrigger`/compatible runner and drains them; the monthly maintenance service is not automatically the chat executor.
- Documentation includes durable status lookup and the provider-neutral `adaptive_runtime.trigger` schema.

- [ ] **Step 1: Write a documentation contract check where the repository already has docs assertions**

```python
def test_chat_doc_no_longer_claims_maintenance_service_executes_chat_events():
    text = Path("docs/LLM_CHAT_TRIGGER.md").read_text(encoding="utf-8")
    assert "maintenance service" in text
    assert "not the chat executor" in text.lower() or "does not automatically execute chat" in text.lower()
```

- [ ] **Step 2: Run the focused documentation test and verify failure**

Run: `pytest tests/test_chat_capability.py -k "maintenance_service" -v`
Expected: FAIL against the current wording that says another host or the existing trigger runtime can drain post-crash work without clarifying the runner ownership boundary.

- [ ] **Step 3: Update recovery/status documentation**

Replace the ambiguous crash-recovery language with exact semantics: the event remains durable; an eligible trigger host can reclaim expired work; `TriggerRuntime` owns persistence/claiming; `AdaptiveRuntime` owns execution; the monthly service remains scheduled maintenance.

- [ ] **Step 4: Run maintenance regression tests**

Run the repository's existing maintenance-service focused test file(s) plus: `pytest tests/test_chat_capability.py -v`.
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/LLM_CHAT_TRIGGER.md tests/test_chat_capability.py
# Include portable/maintenance_service.py only if a compatibility fix was actually required.
git commit -m "docs: clarify adaptive trigger recovery boundary"
```

---

### Task 8: Full Regression, Review, and PR Gate

**Files:**
- All files changed by Tasks 1-7.

**Interfaces:**
- No new public interfaces; this task validates the complete integrated contract.

- [ ] **Step 1: Run the focused trigger suite**

Run: `pytest tests/test_trigger_runtime.py tests/test_adaptive_trigger.py tests/test_chat_capability.py -v`
Expected: PASS.

- [ ] **Step 2: Run the broader repository test suite**

Run the repository-native test command from its documented development workflow (starting with `pytest -q` where applicable). Capture any environment-driven omissions rather than silently ignoring them.

- [ ] **Step 3: Perform static/search verification**

Verify there is exactly one durable trigger table, exactly one AdaptiveTrigger executor pool, no provider-specific runtime logic in `TriggerRuntime`, no `dispatch_once()` path that consumes unrelated kinds, and no documentation statement that promises automatic recovery without a runner host.

- [ ] **Step 4: Create the pull request**

Use title: `fix: harden LLM adaptive runtime trigger`.

The PR body must summarize:
- lease-based crash recovery,
- kind isolation and priority ordering,
- durable status/outcome lookup,
- runtime-owned adapter reuse,
- provider-neutral chat capability,
- package exports and documentation corrections,
- test/verification evidence.

- [ ] **Step 5: Review the PR after creation**

Inspect every changed file, PR discussion, and review thread. Treat substantive findings as blocking. Fix findings in separate commits and rerun focused tests before returning to CI.

- [ ] **Step 6: Verify every applicable GitHub Actions check on the final PR head**

Do not stop at one aggregate status. Enumerate every workflow run triggered for the final head, inspect job conclusions, and confirm no applicable check is skipped because of an incorrect path filter. Check the final commit, not an earlier commit.

- [ ] **Step 7: Merge only after all applicable checks and review evidence are green**

Merge the PR using the repository's normal merge method. Record the resulting merge commit SHA and final CI state.

- [ ] **Step 8: Post-merge verification**

Fetch `main` at the merge commit, verify the merged files are present, and re-check the complete applicable workflow set on the resulting main commit before moving to the next backlog item.

---

## Self-Review Checklist

- [x] Spec coverage: lease recovery, kind isolation, priority, chat exposure, durable status/outcome, adapter reuse, exports, safety boundary, and verification all map to tasks.
- [x] No new scheduler or memory owner is introduced.
- [x] Type/signature flow is consistent: `TriggerRuntime.get()` -> `TriggerStatus`; `AdaptiveTrigger.get_status()` delegates directly; runtime owns one adapter; chat capability invokes the runtime-owned adapter.
- [x] Priority is functional in SQL ordering, not merely stored in payload.
- [x] Recovery is atomic and ownership-safe through `claim_id`.
- [x] Existing monthly maintenance remains a separate scheduled lane.
- [x] Tests are written before implementation in every code task.
