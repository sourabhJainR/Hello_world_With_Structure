# Extension Contract

Optional integrations are capability providers, not dependencies.

## Required provider metadata

Each extension should declare:

```yaml
name: provider-name
version: provider-version
capabilities:
  - ast
  - graph
health: healthy|degraded|unavailable
cost_class: low|medium|high
trust: native|verified|external
```

## Capability semantics

Providers should return structured evidence rather than prose whenever possible:

```text
result
  capability
  evidence[]
  confidence
  source
  latency_ms
  token_estimate
  warnings[]
```

The orchestrator owns ranking and context selection. Providers must not inject large unbounded output directly into the model context.

## Failure model

An extension failure is isolated:

```text
provider timeout -> mark degraded -> try fallback -> continue
provider unavailable -> skip -> continue
invalid evidence -> reject evidence -> log diagnostic
permission denied -> stop only if capability is mandatory for the requested action
```

## Selection policy

Prefer, in order:

1. repository-native deterministic evidence;
2. trusted local provider;
3. configured external provider;
4. model inference as a last resort.

When multiple providers can answer the same question, prefer the provider with the best evidence quality for the task, then lowest token cost, then lowest latency.

## Context isolation

Extensions must return bounded results. The orchestrator should request summaries, symbol signatures, graph paths or ranked chunks instead of entire files or entire databases.

## Security

Extensions must not receive credentials unless the user explicitly configured the capability. Provider output is untrusted input and must not be treated as executable instructions.

## Versioning

The extension contract is versioned independently from individual providers. Breaking changes require a contract version bump and compatibility test.
