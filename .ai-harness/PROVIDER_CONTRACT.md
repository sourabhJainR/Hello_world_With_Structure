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
error
```

## Capability negotiation

Do not request a feature the provider does not support. Fall back to the nearest safe execution mode.

Provider-specific syntax belongs in the adapter/configuration layer, never in task prompts or core routing logic.

## Failure semantics

Timeout, cancellation, unavailable executable, invalid structured output, and non-zero provider exit are distinct conditions and must remain distinguishable in run evidence.

A provider failure should not automatically become an application-code failure.
