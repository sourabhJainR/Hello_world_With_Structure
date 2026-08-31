# Learning and Evolution Policy

Learning is evidence accumulation, not self-modification.

## Memory states

```text
observation -> candidate -> trusted -> deprecated
```

A single model output is an observation only. A later production regression or missed behavior is a high-value negative observation and must remain linked to the original task/run.

## Regression learning

When a completed task later produces a related regression or miss:

1. record the original run ID and immutable intent digest;
2. capture the reported symptom and inspectable evidence IDs;
3. keep the event separate from the product patch;
4. run analysis/RCA first when requested;
5. add the failure pattern as a `regression` learning candidate;
6. require repeated evidence and successful future verification before trusting a corrective pattern.

A regression report never authorizes an automatic product change.

## RCA discipline

RCA is analysis-first. Do not implement a patch when the user asks for RCA only. Establish timeline, actual entry point, flow, data-shape variants, persistence, integrations, logs, tests, history, hypotheses, contradictions and unknowns. Root cause confidence must be `proven`, `probable`, or `unproven` and tied to evidence.

## Promotion

Promote a pattern only when it has repeated observations, acceptable validation success, and no unresolved contradictory evidence. Record observation count, success rate, last-seen time, scope and source runs.

## Decay

Patterns that become stale, fail repeatedly, or conflict with newer repository evidence must lose confidence or be deprecated.

## Immutable zones

Learned memory must never directly modify:

- executable harness code
- provider permissions
- security policy
- approval policy
- dependency allowlists
- repository architecture rules

Those changes require normal implementation, verification, and review. Skill refinement proposals are non-executable until separately evaluated and approved.

## Learning targets

Prefer learning:

- routing accuracy
- useful context sources
- verification effectiveness
- common failure modes
- repository-specific conventions
- successful repair strategies
- recurring regression patterns
- token/tool efficiency
- useful task boundaries and non-goals

Do not optimize for raw speed if it reduces correctness or verification quality.
