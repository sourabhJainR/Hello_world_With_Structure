# Provider Contract

A provider is an execution adapter, not the orchestration brain.

## Required semantics

The adapter should expose, when supported:

- provider identifier
- model identifier
- reasoning/effort tier
- supported tools
- structured output capability
- streaming capability
- cancellation
- timeout behavior
- token/input/output usage
- exit status
- tool-call or step observations when the provider exposes them
- prompt-cache capability when the provider exposes it

## Agent-loop contract

The provider-facing loop should preserve the following semantic cycle even when provider-specific APIs differ:

```text
plan -> tool/action -> observation -> verify -> continue/stop
```

A tool result is an observation, not a completion signal. A model statement such as "done", "verified", or "no regression" is not accepted as proof without repository evidence.

When a provider exposes intermediate tool calls, the adapter should preserve their order, tool name, duration, status, and compact result digest. When the provider does not expose them, the harness records the phase-level observation instead of inventing tool telemetry.

## Context cache contract

The harness may provide content-addressed context pages. Provider adapters may map stable page digests to native prompt-cache facilities when supported.

The adapter must not claim a cache hit unless the provider reports one. `provider_kv_cache = adapter-dependent` is the safe default.

Stable context should be reused where the provider supports prefix/prompt caching. Dynamic task evidence, current diffs, failures, and verification output should remain separate from stable context so cache invalidation is narrow.

## Normalized result

The orchestrator should normalize provider output into:

```text
status
provider
model
phase
duration
usage
artifacts
text
structured_data
tool_observations
cache
error
```

`cache` should distinguish harness page reuse from provider-side prompt/KV-cache hits.

## Capability negotiation

Do not request a feature the provider does not support. Fall back to the nearest safe execution mode.

Provider-specific syntax belongs in the adapter/configuration layer, never in task prompts or core routing logic.

## Failure semantics

Timeout, cancellation, unavailable executable, invalid structured output, and non-zero provider exit are distinct conditions and must remain distinguishable in run evidence.

A provider failure should not automatically become an application-code failure.
