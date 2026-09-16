# LLM Adaptive Runtime Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral LLM-chat trigger that durably records an AdaptiveRuntime execution request and returns immediately, while reusing the existing durable trigger/scheduler infrastructure and the existing cross-platform maintenance service.

**Architecture:** Extend the existing `TriggerRuntime` with a focused chat-facing adapter rather than creating another queue, scheduler, or learning store. A trigger is persisted before acknowledgement, then claimed by a bounded dispatcher and handed to `AdaptiveRuntime.run`; the existing maintenance service continues to own scheduled maintenance and learning consolidation. The chat API returns a durable receipt containing a trigger ID and status without waiting for orchestration completion.

**Tech Stack:** Python 3, dataclasses, SQLite/WAL, existing `TriggerRuntime`, `AutomationScheduler`, `AdaptiveRuntime`, pytest, existing GitHub Actions harnesses.

**Spec:** `docs/superpowers/specs/2026-09-17-llm-adaptive-runtime-trigger-design.md`

## Global Constraints

- The feature is additive to `portable.maintenance_service`; it must not replace or fork the OS service lifecycle.
- `AutomationScheduler` remains the source of truth for scheduled maintenance and existing interval/calendar schedules remain compatible.
- Trigger intake must be durable before the caller receives its acknowledgement.
- Chat retries must be safe through optional caller-supplied `event_id` idempotency.
- Trigger execution must reuse `AdaptiveRuntime.run`, including verification/evidence/learning behavior already owned by that runtime.
- No unbounded background threads, second persistent queues, or second learning/memory stores may be introduced.
- Trigger execution must fail closed on invalid payloads and must expose durable terminal/retryable state.

## File Map

- Create `portable/adaptive_trigger.py` for the provider-neutral chat-facing request/receipt facade and bounded fire-and-forget dispatch entry point.
- Modify `portable/trigger_runtime.py` only where needed to expose durable trigger status/claim metadata without changing its existing event semantics.
- Modify `portable/adaptive_runtime.py` to expose one composition-level trigger method that delegates to the new facade while preserving direct synchronous `run()` behavior.
- Modify `portable/maintenance_service.py` only if needed to provide an optional dispatch pass for chat-triggered work; the monthly maintenance schedule remains unchanged.
- Create focused tests under `tests/` for intake, idempotency, dispatch, retry/failure state, and service coexistence.
- Modify `README.md` with the LLM-chat trigger contract and examples after code is working.

### Task 1: Define the durable chat trigger contract

**Files:**
- Create: `portable/adaptive_trigger.py`
- Test: `tests/test_adaptive_trigger.py`

**Interfaces:**
- Consumes: `TriggerRuntime` and an `AdaptiveRuntime` runner callback.
- Produces: `AdaptiveTriggerRequest`, `TriggerReceipt`, and `AdaptiveTrigger` methods `trigger_adaptive_runtime(...)` and `dispatch_once(...)`.

- [ ] **Step 1: Write the failing tests for request validation and receipt shape**

```python
def test_trigger_requires_task_and_project_root():
    trigger = AdaptiveTrigger(trigger_runtime, runner=lambda request: None)
    with pytest.raises(ValueError):
        trigger.trigger_adaptive_runtime("", "/repo", {})


def test_trigger_persists_before_returning_receipt():
    receipt = trigger.trigger_adaptive_runtime("fix bug", "/repo", {"source": "chat"})
    assert receipt.trigger_id
    assert receipt.status == "pending"
    assert trigger_runtime.due(limit=1)[0].event_id == receipt.trigger_id
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: collection/import failure because `portable.adaptive_trigger` and its public types do not yet exist.

- [ ] **Step 3: Implement the minimal immutable request and receipt types**

```python
@dataclass(frozen=True)
class AdaptiveTriggerRequest:
    task: str
    project_root: str
    context: Mapping[str, Any]
    priority: str = "normal"


@dataclass(frozen=True)
class TriggerReceipt:
    trigger_id: str
    status: str
    accepted_at: str
```

Validate non-empty task/project root, allow only `low|normal|high` priority, and keep context JSON-compatible through the existing `TriggerRuntime.emit()` validation path.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: PASS for validation/receipt tests.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_trigger.py tests/test_adaptive_trigger.py
git commit -m "feat: define adaptive chat trigger contract"
```

### Task 2: Add idempotent fire-and-forget intake

**Files:**
- Modify: `portable/adaptive_trigger.py`
- Modify: `portable/trigger_runtime.py` only if a small status helper is required by tests
- Test: `tests/test_adaptive_trigger.py`

**Interfaces:**
- Consumes: `AdaptiveTriggerRequest`.
- Produces: `AdaptiveTrigger.trigger_adaptive_runtime(task, project_root, context, priority="normal", event_id=None, max_attempts=3) -> TriggerReceipt`.

- [ ] **Step 1: Write failing tests for idempotent retries and payload normalization**

```python
def test_same_event_id_returns_same_trigger():
    first = trigger.trigger_adaptive_runtime("task", "/repo", {"x": 1}, event_id="chat-42")
    second = trigger.trigger_adaptive_runtime("task", "/repo", {"x": 1}, event_id="chat-42")
    assert second.trigger_id == first.trigger_id
    assert len(trigger_runtime.due(limit=10)) == 1


def test_reused_event_id_with_changed_payload_is_rejected():
    trigger.trigger_adaptive_runtime("task", "/repo", {"x": 1}, event_id="chat-42")
    with pytest.raises(ValueError):
        trigger.trigger_adaptive_runtime("other", "/repo", {"x": 1}, event_id="chat-42")
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pytest tests/test_adaptive_trigger.py -k "same_event_id or reused_event_id" -v`
Expected: FAIL until the facade maps the chat request to one canonical durable trigger payload.

- [ ] **Step 3: Implement the intake mapping**

```python
def trigger_adaptive_runtime(...):
    request = AdaptiveTriggerRequest(task=task, project_root=str(Path(project_root).expanduser().resolve()), context=dict(context or {}), priority=priority)
    event = self.trigger_runtime.emit(
        "adaptive_runtime",
        {"task": request.task, "project_root": request.project_root, "context": dict(request.context), "priority": request.priority},
        event_id=event_id,
        max_attempts=max_attempts,
    )
    return TriggerReceipt(event.event_id, event.status, event.created_at)
```

The method must return immediately after durable persistence; it must never call `AdaptiveRuntime.run()` inline.

- [ ] **Step 4: Run tests and verify idempotency**

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: PASS, with one durable event for repeated chat delivery using the same `event_id`.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_trigger.py portable/trigger_runtime.py tests/test_adaptive_trigger.py
git commit -m "feat: add durable idempotent adaptive trigger intake"
```

### Task 3: Dispatch triggers into the existing AdaptiveRuntime

**Files:**
- Modify: `portable/adaptive_trigger.py`
- Modify: `portable/adaptive_runtime.py`
- Test: `tests/test_adaptive_trigger.py`

**Interfaces:**
- Consumes: durable `TriggerEvent(kind="adaptive_runtime")`.
- Produces: `AdaptiveTrigger.dispatch_once(limit=20) -> list[TriggerOutcome]` and `AdaptiveRuntime.trigger_adaptive_runtime(...) -> TriggerReceipt`.

- [ ] **Step 1: Write failing dispatch tests**

```python
def test_dispatch_calls_adaptive_runtime_runner_once():
    calls = []
    trigger = AdaptiveTrigger(trigger_runtime, runner=lambda request: calls.append(request))
    receipt = trigger.trigger_adaptive_runtime("fix bug", "/repo", {"source": "chat"})
    trigger.dispatch_once()
    assert calls[0].task == "fix bug"
    assert trigger_runtime.due(limit=10) == ()
```

- [ ] **Step 2: Run the dispatch test and verify failure**

Run: `pytest tests/test_adaptive_trigger.py::test_dispatch_calls_adaptive_runtime_runner_once -v`
Expected: FAIL because dispatch is not implemented.

- [ ] **Step 3: Implement one-pass durable claim/dispatch**

```python
def dispatch_once(self, *, limit: int = 20) -> list[TriggerOutcome]:
    def handler(event: TriggerEvent):
        payload = event.payload
        result = self.runner(AdaptiveTriggerRequest(
            task=str(payload["task"]),
            project_root=str(payload["project_root"]),
            context=dict(payload.get("context", {})),
            priority=str(payload.get("priority", "normal")),
        ))
        return TriggerOutcome(event.event_id, "accepted", result)
    return self.trigger_runtime.dispatch_due(handler, limit=limit)
```

Adapt the runner so it invokes `AdaptiveRuntime.run()` with generated stable `session_id`/`task_id` values derived from the trigger ID rather than exposing trigger execution as a second runtime. Keep the existing synchronous `run()` API unchanged.

- [ ] **Step 4: Add composition-level trigger API on `AdaptiveRuntime` and test it**

```python
def trigger_adaptive_runtime(self, task, project_root, context=None, *, priority="normal", event_id=None, max_attempts=3):
    return self.adaptive_trigger.trigger_adaptive_runtime(task, project_root, context or {}, priority=priority, event_id=event_id, max_attempts=max_attempts)
```

Instantiate the facade once in `AdaptiveRuntime.__init__` using the existing `TriggerRuntime` and a runner closure bound to the same runtime instance.

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: PASS for intake, idempotency, and dispatch integration.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_trigger.py portable/adaptive_runtime.py tests/test_adaptive_trigger.py
git commit -m "feat: dispatch chat triggers through adaptive runtime"
```

### Task 4: Make failures, retries, and fire-and-forget semantics explicit

**Files:**
- Modify: `portable/adaptive_trigger.py`
- Modify: `portable/trigger_runtime.py` only if status inspection needs a small read-only query
- Test: `tests/test_adaptive_trigger.py`

**Interfaces:**
- Consumes: claimed durable triggers.
- Produces: durable success/retryable/failed states and a read-only `status(trigger_id)` method returning the current `TriggerEvent`.

- [ ] **Step 1: Write failure/retry tests**

```python
def test_runner_exception_is_retryable_then_terminal():
    attempts = []
    def failing_runner(request):
        attempts.append(request)
        raise RuntimeError("boom")
    trigger = AdaptiveTrigger(trigger_runtime, runner=failing_runner)
    receipt = trigger.trigger_adaptive_runtime("task", "/repo", {}, max_attempts=2)
    trigger.dispatch_once()
    event = trigger.status(receipt.trigger_id)
    assert event.status == "pending"
    assert event.attempts == 1
```

- [ ] **Step 2: Run and verify failure before implementation**

Run: `pytest tests/test_adaptive_trigger.py -k "retryable or terminal" -v`
Expected: FAIL until status access and bounded retry behavior are covered by the facade.

- [ ] **Step 3: Implement read-only status and explicit outcome handling**

```python
def status(self, trigger_id: str) -> TriggerEvent:
    event = self.trigger_runtime.get(trigger_id)
    if event is None:
        raise KeyError(trigger_id)
    return event
```

Preserve `TriggerRuntime` exponential retry/backoff and claim-before-run behavior. Never swallow a runner exception as success. Do not report orchestration completion to chat at intake time; only the receipt status is guaranteed immediately.

- [ ] **Step 4: Run trigger tests**

Run: `pytest tests/test_adaptive_trigger.py -v`
Expected: PASS for retryable and terminal failure behavior, including idempotent redelivery.

- [ ] **Step 5: Commit**

```bash
git add portable/adaptive_trigger.py portable/trigger_runtime.py tests/test_adaptive_trigger.py
git commit -m "test: harden adaptive trigger retry semantics"
```

### Task 5: Integrate coexistence with the existing maintenance service

**Files:**
- Modify: `portable/maintenance_service.py` only if required
- Modify: `portable/adaptive_runtime.py`
- Test: `tests/test_maintenance_service.py` or the repository's existing service test module

**Interfaces:**
- Consumes: existing service configuration and scheduler ownership.
- Produces: optional bounded trigger-dispatch pass that does not alter the monthly maintenance schedule.

- [ ] **Step 1: Write a coexistence regression test**

```python
def test_chat_trigger_does_not_replace_monthly_maintenance_schedule(tmp_path):
    runtime = make_runtime(tmp_path)
    runtime.ensure_learning_maintenance(tmp_path)
    maintenance_before = runtime.automation_scheduler.find_task(
        json.dumps({"kind": "adaptive_learning", "project_root": str(tmp_path.resolve())}, sort_keys=True)
    )
    receipt = runtime.trigger_adaptive_runtime("chat task", tmp_path, {"source": "chat"})
    assert receipt.trigger_id
    maintenance_after = runtime.automation_scheduler.find_task(
        json.dumps({"kind": "adaptive_learning", "project_root": str(tmp_path.resolve())}, sort_keys=True)
    )
    assert maintenance_after.id == maintenance_before.id
```

- [ ] **Step 2: Run the service coexistence test**

Run: `pytest tests/test_maintenance_service.py -k "coexistence or monthly" -v`
Expected: PASS after implementation; currently it may fail if the new facade is not wired correctly.

- [ ] **Step 3: Add only the minimal service hook required for external dispatch**

The service must retain its existing role. When a host needs the service process to drain chat-triggered events, expose a bounded dispatch operation or call it from the existing foreground loop without changing monthly maintenance timing. Do not create a second SQLite database, schedule, or maintenance worker.

- [ ] **Step 4: Run the relevant scheduler/service suite**

Run: `pytest tests/test_maintenance_service.py tests/test_automation_scheduler.py -v`
Expected: all existing scheduler/service tests plus the new coexistence test pass.

- [ ] **Step 5: Commit**

```bash
git add portable/maintenance_service.py portable/adaptive_runtime.py tests/test_maintenance_service.py tests/test_automation_scheduler.py
git commit -m "feat: integrate chat triggers without changing maintenance service"
```

### Task 6: Document LLM-chat integration and run the full regression suite

**Files:**
- Modify: `README.md`
- Modify: package exports if the repository convention requires them
- Test: existing full test suites and CI workflows

**Interfaces:**
- Consumes: stable `AdaptiveRuntime.trigger_adaptive_runtime(...)` API.
- Produces: documented provider-neutral chat/tool invocation contract.

- [ ] **Step 1: Add README examples**

Document the minimal chat-side flow:

```python
receipt = runtime.trigger_adaptive_runtime(
    task="Improve the repository retrieval strategy",
    project_root="/workspace/repo",
    context={"source": "llm-chat", "conversation_id": "..."},
    priority="normal",
    event_id="chat-event-123",
)
# returns immediately; inspect receipt.trigger_id and later status()
```

Explain that the OS maintenance service remains independently scheduled for monthly maintenance, while chat-triggered work is an on-demand execution path using the same durable trigger store and AdaptiveRuntime learning lifecycle.

- [ ] **Step 2: Run focused unit tests**

Run: `pytest tests/test_adaptive_trigger.py tests/test_maintenance_service.py tests/test_automation_scheduler.py -v`
Expected: PASS.

- [ ] **Step 3: Run the repository's complete test/validation commands**

Run the commands documented by the repository CI workflows, including the graph runtime, harness, architecture integrity, portable bundle, and production hardening checks where available in the current branch.
Expected: every check passes; do not stop at a single named workflow.

- [ ] **Step 4: Commit documentation and any package export changes**

```bash
git add README.md portable tests
git commit -m "docs: document LLM fire-and-forget adaptive trigger"
```

- [ ] **Step 5: Create PR, review, fix findings, wait for CI, then merge**

Create the feature PR against `main`. Review the complete diff and all review threads. Fix every substantive finding, push the fixes, wait for every required workflow to finish, and verify every check is green before merging. After merge, confirm the merge commit and final main status.
