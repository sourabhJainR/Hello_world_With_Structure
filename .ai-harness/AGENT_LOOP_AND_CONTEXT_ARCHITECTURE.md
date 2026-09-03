# Agent Loop and Context Architecture

## What this repository implements

The harness is a control plane around provider-owned coding-agent loops. The provider executes the model/tool loop; the harness owns routing, context, safety, verification, persistence, and learning.

The target execution cycle is:

```text
INTENT
  -> PLAN
  -> EXPLORE
  -> ACT
  -> OBSERVE
  -> VERIFY
  -> DECIDE
       |-- done -> REPORT
       |-- repair -> ACT
       |-- uncertainty -> EXPLORE/RESEARCH
       |-- scope/risk violation -> STOP
```

This follows the ReAct-style reason/act/observe loop described by Decoding AI, while keeping the implementation provider-neutral. The model is not treated as the source of truth for completion; verification evidence is.

## SOLID and architecture boundaries

- Single Responsibility: routing, context selection, execution controls, verification, learning, and provider execution remain separate modules.
- Open/Closed: providers and optional knowledge extensions are configured adapters rather than hard-coded task logic.
- Liskov: provider adapters must preserve the normalized provider contract and distinguish execution failures from application failures.
- Interface Segregation: capability contracts expose only the operations needed by the phase.
- Dependency Inversion: policy depends on provider/capability contracts, not a concrete CLI implementation.

These principles are constraints applied proportionally; they do not justify speculative abstraction.

## KV cache and PagedAttention: correct use in a coding harness

KV caching and PagedAttention are model-serving mechanisms. The harness must not claim to implement GPU attention caching unless it owns the model-serving layer.

Instead, this repository applies the transferable systems ideas at the prompt/context layer:

1. Stable prefix: keep repository rules and task contract stable.
2. Content-addressed pages: split reusable context into immutable pages identified by digest.
3. Reuse: unchanged pages are reused in-process rather than rebuilt.
4. Paging: only pages that fit the current budget are selected.
5. Locality: task-relevant evidence is ranked before page selection.
6. Provenance: page IDs are included in context metadata.
7. Verification pinning: acceptance evidence, failures, security findings, and required checks are not discarded by ordinary compaction.

This is analogous to virtual-memory/page allocation, not an implementation of PagedAttention. A provider adapter may later map stable page digests to provider-native prompt caching where supported.

## Important limitation

A CLI wrapper cannot guarantee provider-side KV-cache hits. The context cache reduces harness-side context preparation and creates a clean seam for provider caching; actual token billing/latency improvements require provider support and measurement.

## Loop quality rules

Every meaningful cycle should answer:

- What is the current goal?
- What evidence was observed?
- What action follows from that evidence?
- What changed?
- What verification proves the change?
- Is the next action still within scope?
- Is another cycle expected to add measurable value?

Retries without new evidence are rejected. High-risk work requires stronger verification and independent review.

## Metrics to expose

At minimum, record:

- context budget and selected characters/tokens
- page count and cache hit rate
- model/provider and reasoning tier when available
- tool/phase duration
- verification result
- repair count
- regression count
- final evidence score
- reason for stopping

These metrics allow the team to test whether the architecture improves outcomes rather than relying on design claims.
