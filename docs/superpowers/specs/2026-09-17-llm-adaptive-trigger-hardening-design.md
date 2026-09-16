# LLM Adaptive Trigger Hardening Design

## Goal
Harden the LLM-chat AdaptiveRuntime trigger so it is durable across crashes, isolated by trigger kind, priority-aware, observable through durable status, reusable by host integrations, and directly exposed as a provider-neutral chat capability while preserving the existing cross-platform maintenance service.

## Architecture
The existing `TriggerRuntime` remains the single durable event substrate. Trigger claims gain a lease so a crashed worker cannot permanently strand work; due selection can filter by event kind and order by explicit priority plus FIFO sequence. `AdaptiveTrigger` remains the on-demand chat lane and invokes the same `AdaptiveRuntime.run()` path; the OS maintenance service remains the scheduled learning lane.

## Data flow
```text
LLM chat / tool
    |
    v
AdaptiveTrigger
    |
    +--> persist event: kind, priority, payload
    |
    +--> return TriggerReceipt immediately
    |
    v
bounded dispatcher
    |
    v
TriggerRuntime claim(kind, id) + lease
    |
    v
AdaptiveRuntime.run()
    |
    +--> normal verification / evidence / learning
    |
    v
TriggerRuntime completion + outcome
```

## Durability and recovery
Every claim records `claimed_at` and `lease_until`. A pending selection may reclaim a claimed event whose lease has expired. Reclamation clears the stale claim atomically and increments no attempt counter until the new worker successfully claims the event. Completion remains ownership-checked by `claim_id`.

The existing retry/backoff semantics remain authoritative. A crashed worker therefore leaves durable work recoverable rather than permanently stuck.

## Trigger isolation
`TriggerRuntime.due()` accepts an optional `kind` filter and priority ordering. `AdaptiveTrigger` always requests only `adaptive_runtime` events. Other trigger kinds remain invisible to the chat dispatcher.

## Priority
Adaptive trigger priorities are `high`, `normal`, and `low`. Due ordering is priority descending, then availability time, then durable sequence/event ID for deterministic FIFO behavior within a priority.

## Chat/tool exposure
Add a provider-neutral capability descriptor for `adaptive_runtime.trigger` with a stable input/output schema. The existing Claude/plugin integration can expose that capability without binding runtime semantics to a single provider. The API returns a durable `TriggerReceipt`; it does not wait for execution.

## Status and outcomes
Expose durable lookup by trigger ID with status, attempts, max attempts, priority, available time, claim state, completion time, and bounded detail. Successful executions can retain a compact serialized outcome reference without requiring an in-memory future to remain alive.

## Adapter lifecycle
`AdaptiveTrigger` uses the process-wide bounded executor for fire-and-forget dispatch. Convenience calls do not create or shut down executors per request. Long-lived hosts may keep one adapter instance and call `dispatch_once()` when they own draining explicitly.

## Package surface
Export `AdaptiveTrigger`, `AdaptiveTriggerRequest`, `TriggerOutcome`, `TriggerReceipt`, and `trigger_adaptive_runtime` from `portable`.

## Safety boundaries
The chat trigger does not bypass verification, evidence, permissions, policy gates, or active-task policy. The monthly maintenance service remains unchanged as the scheduled maintenance lane and may only drain durable work through explicit host policy; it does not become the owner of chat semantics.

## Verification
Regression coverage must prove lease recovery, kind isolation, priority ordering, concurrent single-owner claims, durable status/outcome visibility, convenience API reuse, chat capability schema, package exports, and preservation of all existing maintenance-service behavior.