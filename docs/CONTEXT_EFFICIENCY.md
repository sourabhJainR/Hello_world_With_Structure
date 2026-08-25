# Context Efficiency and Quality Policy

The orchestrator optimizes for **verified outcome per model token**, not minimum tokens at any cost.

## 1. Keep always-loaded instructions small

Always-loaded agent instructions should contain only rules that are hard to infer from the repository and must be obeyed on every task. Do not repeat architecture, tool documentation, examples, or detailed workflows that the agent can discover when needed.

Prefer:

- repository-specific commands that are otherwise non-obvious
- non-obvious invariants
- required verification commands
- safety boundaries
- important naming/placement rules

Avoid generated inventories, long tutorials, duplicated tool documentation, and generic advice.

## 2. Retrieve, do not replay

Never inject the whole repository, whole memory store, whole graph, or full conversation when a targeted query can provide the required evidence.

Retrieval order:

`task contract -> local rules -> symbols -> graph paths -> exact search -> semantic search -> targeted source -> verification evidence`

Every retrieved item should have a reason for inclusion and provenance where available.

## 3. Budget context by task phase

Use separate budgets for:

- bootstrap/context discovery
- planning
- implementation
- verification
- review
- handoff

Do not let a large discovery phase consume the entire implementation context.

When a phase becomes context-heavy, summarize durable state into a compact handoff and start the next phase with fresh context.

## 4. Use small executable units

For complex work, decompose into independently verifiable slices. Prefer a sequence of small tasks with explicit acceptance criteria over one giant autonomous task. A slice should be small enough that its implementation and verification evidence remain easy to inspect.

Do not create artificial subtasks when the task is already simple.

## 5. Fresh-context verification

For meaningful changes, verification should be planned from the acceptance criteria rather than copied from the implementation. When practical, use a fresh reviewer/verification context that did not author the change.

The verifier must answer:

1. What behavior must be true?
2. What evidence would prove it?
3. What could make the current test pass while the feature is still wrong?
4. Are negative, boundary, compatibility, and failure paths covered?

## 6. Repository entropy check

After substantial work, inspect the change surface for stale documentation, contradictory comments, dead code, obsolete tests, temporary artifacts, merge-conflict remnants, and inconsistent behavior descriptions.

Do not turn cleanup into an unrelated refactor. Fix only contradictions or artifacts caused by, or materially blocking, the current task.

## 7. Cache stable evidence when the provider supports it

Reuse immutable or slow-changing evidence such as repository profile, symbol index, dependency graph, and stable instructions. Do not repeatedly retrieve identical content merely because a new model call started.

Cache invalidation must be tied to repository state, relevant file hashes, branch/commit, and provider version where available.

## 8. Route models and tools by difficulty

Use the least expensive capable model/provider for deterministic discovery, extraction, formatting, and simple checks. Reserve stronger reasoning models for ambiguous planning, architecture, difficult debugging, and final judgment.

Do not spawn a sub-agent when the parent can complete the task with less total context and fewer calls.

## 9. Optimize for total cost, not input tokens alone

Track, when available:

- input tokens
- cached input tokens
- output tokens
- tool calls
- wall-clock time
- retries
- context compactions
- verification failures
- final outcome

A shorter prompt that causes three retries is worse than a slightly larger prompt that succeeds once.

## 10. Learn from measured outcomes

Use evals and telemetry to identify which retrieval, routing, provider, and verification strategies improve task success. Do not promote a change because it merely reduced token count.

Primary objective:

`quality first -> reliability -> token efficiency -> latency -> cost`

A token-saving optimization that reduces verified task success must be rejected.
