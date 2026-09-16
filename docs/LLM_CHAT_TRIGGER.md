# LLM Chat AdaptiveRuntime Trigger

AER exposes a provider-neutral, fire-and-forget trigger for an LLM chat, agent adapter, or other interactive caller that needs to start normal `AdaptiveRuntime` execution without waiting for the full orchestration lifecycle.

## Flow

```text
LLM chat / tool call
        |
        v
AdaptiveTrigger.trigger_adaptive_runtime()
        |
        +--> durable TriggerRuntime event
        |
        +--> bounded background dispatch
        v
AdaptiveRuntime.run()
        |
        +--> verification / evidence
        +--> experience record
        +--> deferred learning
        v
existing maintenance service
```

The trigger and the maintenance service are complementary. The trigger is an on-demand execution path; the OS service continues to own the scheduled last-day-of-month maintenance cycle. Neither creates a second memory store or scheduler.

## Python API

```python
from portable.adaptive_trigger import AdaptiveTrigger

trigger = AdaptiveTrigger.for_runtime(runtime)
receipt = trigger.trigger_adaptive_runtime(
    task="Improve repository retrieval for authentication changes",
    project_root="/workspace/repo",
    context={"source": "llm-chat", "conversation_id": "chat-123"},
    priority="normal",
    event_id="chat-event-123",
)
```

The call returns a `TriggerReceipt` immediately after the execution intent is durably persisted. The default `fire_and_forget=True` schedules bounded background dispatch; the caller does not wait for `AdaptiveRuntime.run()` to complete.

For an adapter that only wants to enqueue work and let an existing host drain it:

```python
receipt = trigger.trigger_adaptive_runtime(
    task="Re-evaluate the API timeout strategy",
    project_root="/workspace/repo",
    context={"source": "llm-chat"},
    fire_and_forget=False,
)
trigger.dispatch_once()
```

A simple convenience entry point is also available:

```python
from portable.adaptive_trigger import trigger_adaptive_runtime

receipt = trigger_adaptive_runtime(
    runtime,
    "Learn from this completed repository task and evaluate the strategy",
    "/workspace/repo",
    {"source": "llm-chat"},
)
```

## Idempotency and recovery

Pass a stable `event_id` when the chat/tool layer may retry a request. Reusing the same ID with the same payload returns the existing durable trigger rather than creating duplicate work. Reusing it with different content fails closed.

The trigger uses `TriggerRuntime` claim-before-run semantics. If the background worker or caller process disappears after persistence, the pending event remains durable and can be drained later by another host using `dispatch_once()` or the existing trigger runtime. AdaptiveRuntime itself remains the only owner of orchestration, evidence, and learning behavior.

## Safety boundaries

The trigger does not bypass AER verification, review, evidence, policy, or learning gates. Chat context is passed into the normal `AdaptiveRuntime.run()` path; it does not create a privileged execution path. The background dispatcher is bounded to a shared four-worker pool so many chat requests cannot create one unbounded thread per request.
