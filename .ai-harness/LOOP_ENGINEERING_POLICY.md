# Loop Engineering Policy

The orchestrator uses a bounded quality loop inspired by the six-layer model:

1. Generation: produce the smallest useful candidate.
2. Evaluation: verify correctness, acceptance, regressions, and evidence.
3. Memory: retain compact evidence-backed outcomes and trusted lessons.
4. Scheduling: decide the next best action.
5. Optimization: improve context, routing, and collaboration efficiency.
6. Recursion: repeat only when explicitly enabled and measurable value remains.

## Smart collaboration

Subagents are selected by complexity and risk, not by a fixed swarm.

- Planner establishes intent, boundaries, and proof obligations.
- Builder changes code or artifacts.
- Evaluator verifies behavior and evidence.
- Reviewer is added for high-risk or complex work.
- Optimizer is added for difficult research, RCA, or high-context work.

Independent read-only analysis may run in parallel. Conflicting edits never run in parallel.

## Graph and memory

Knowledge remains a provenance graph:

`Evidence -> Finding -> Decision -> Change -> Verification -> Outcome -> Learning`

Handoffs carry only the next component's useful state. Full transcripts are not replayed.

## Stop conditions

Stop when any of these is true:

- iteration budget reached;
- quality is sufficient and regressions are absent;
- marginal utility falls below the configured threshold;
- no new evidence is produced;
- the next iteration would only restate or cosmetically rewrite the same result.

The default runtime remains one adaptive run. Explicit loop mode is bounded to prevent runaway cost or recursive self-invocation.

## Quality objective

Optimize for verified artifact quality per token, tool call, retry, and latency. More iterations are not automatically better. A loop earns another cycle only when it can demonstrate likely improvement.
