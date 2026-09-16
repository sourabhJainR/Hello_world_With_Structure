# LLM Chat to AdaptiveRuntime Fire-and-Forget Trigger

## Purpose

Add a chat-facing trigger boundary that lets an LLM interaction request an `AdaptiveRuntime` execution without blocking on the execution result. This capability is additive to the existing OS maintenance service and must reuse the repository's durable trigger/scheduling state rather than creating a second learning system.

## Goals

- Accept a structured task request from an LLM chat/tool integration.
- Persist the trigger before acknowledging the chat request.
- Return immediately with a durable trigger receipt and stable `trigger_id`.
- Execute `AdaptiveRuntime.run(...)` asynchronously through the existing durable trigger machinery.
- Preserve existing verification, memory, learning, adaptive-policy, and maintenance behavior.
- Support idempotent retries from chat/tool providers using an optional caller-supplied `event_id`.
- Survive process restart without losing an accepted trigger.
- Keep execution bounded and fail closed: trigger intake must not bypass existing runtime gates.

## Non-goals

- Replacing the OS service or its monthly scheduler.
- Adding a second durable queue/database.
- Making LLM chat itself responsible for long-running orchestration.
- Allowing a trigger to bypass verification, safety/quality gates, or adaptive-policy controls.
- Introducing provider-specific LLM APIs into the core runtime.

## Architecture

```text
LLM Chat / Tool
      |
      | trigger_adaptive_runtime(...)
      v
Chat Trigger Adapter
      |
      | persist before acknowledgement
      v
TriggerRuntime (durable inbox + claim/retry)
      |
      | claimed event
      v
Bounded Async Dispatcher
      |
      v
AdaptiveRuntime.run(...)
      |
      +--> experience record
      +--> deferred learning job
      +--> existing continuous maintenance lane
      +--> existing memory/consolidation/tuning

Existing OS maintenance service remains unchanged and continues to drive scheduled maintenance.
```

### Core API

Provide a provider-neutral API equivalent to:

```python
trigger_adaptive_runtime(
    task: str,
    project_root: str | Path,
    context: Mapping[str, Any] | None = None,
    priority: str = "normal",
    event_id: str | None = None,
) -> TriggerReceipt
```

The default behavior is fire-and-forget. The call persists an intent and returns without waiting for orchestration completion.

`TriggerReceipt` contains at least:

- `trigger_id`
- `status` (`accepted`, `already_accepted`, or rejection/error information)
- `created_at`
- task/project identifiers suitable for audit and later lookup

The trigger payload is JSON-compatible and contains enough data to reconstruct the eventual `AdaptiveRuntime.run` request. Sensitive data must continue to follow the repository's existing redaction/storage boundaries.

## Durable dispatch

`TriggerRuntime` remains the durable source of truth. The new adapter emits a typed adaptive-runtime trigger event. A bounded dispatcher claims pending events and invokes `AdaptiveRuntime.run`.

The dispatcher must:

1. claim exactly one event owner using existing claim semantics;
2. invoke the runtime outside the database transaction;
3. mark success only after the runtime returns successfully;
4. mark retryable on transient execution errors using existing backoff;
5. stop retrying at the configured attempt bound;
6. record concise failure detail for diagnosis;
7. avoid creating duplicate execution for the same accepted event.

An in-memory worker may be used to provide the immediate asynchronous handoff, but persistence is authoritative. Recovery must be possible by polling/dispatching pending events after restart.

## Relationship to the maintenance service

The existing `portable.maintenance_service` remains the operating-system host for continuous/background maintenance. This feature is a separate ingress path from LLM chat into the adaptive runtime.

The two paths share durable scheduler/memory/runtime state:

- Chat trigger: on-demand execution request, fire-and-forget.
- Maintenance service: scheduled maintenance/consolidation/tuning.

A chat-triggered run may create deferred learning work, which the existing maintenance lane later processes. The chat trigger must not start a competing maintenance loop.

## Priority and fairness

Priority is an intake hint, not a bypass of safety or bounded execution. The dispatcher should preserve deterministic ordering within a priority class while remaining bounded by a configurable batch/worker limit. The initial implementation should support `normal` plus a lower/higher priority representation only where the current trigger storage can represent it cleanly; avoid unrelated scheduler redesign.

## Idempotency

When `event_id` is supplied, duplicate submissions with identical content return the original durable receipt rather than creating another execution. Reusing the same `event_id` with different task content is rejected. This protects against LLM/tool retries, network retries, and user-visible replays.

## Error handling

- Invalid task/project root/payload: reject synchronously and do not persist.
- Persistence failure: reject synchronously because no accepted trigger may be reported without durable state.
- Runtime transient failure: persist `retryable` and let existing retry/backoff handle later dispatch.
- Runtime terminal failure: persist `failed` and expose the failure through the trigger status/lookup API.
- Process crash after persistence and before execution: pending event remains recoverable.

## Chat integration surface

The implementation should expose a small, provider-neutral callable/tool surface that an LLM host can invoke. Documentation must show the request/response shape and explicitly state that the response is an acknowledgement, not task completion.

A CLI-compatible entry point may also be provided for local/manual testing, but it is an adapter over the same trigger API rather than a separate execution implementation.

## Testing

Add tests for:

- synchronous persistence and immediate receipt;
- idempotent duplicate event submission;
- rejection of conflicting reused event IDs;
- asynchronous dispatch into `AdaptiveRuntime.run` without blocking the caller;
- successful completion;
- retryable failure and bounded backoff;
- terminal failure after max attempts;
- restart/recovery semantics for pending events;
- malformed/non-JSON trigger payloads;
- coexistence with the existing maintenance service and scheduler;
- regression coverage showing `AdaptiveRuntime` learning/maintenance behavior remains unchanged.

Run the repository's full required workflow matrix and verify every check before merge, not only the checks directly related to the feature.

## Success criteria

The feature is complete when an LLM chat/tool call can durably enqueue an `AdaptiveRuntime` task, receive an immediate trigger receipt, and have the task execute asynchronously without introducing a second scheduler or learning state; pending work survives restart; retries are bounded and idempotent; existing maintenance service behavior remains intact; documentation describes both ingress paths; and all repository CI checks are green.
