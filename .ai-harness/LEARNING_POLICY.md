# Learning and Evolution Policy

Learning is evidence accumulation, not self-modification.

## Memory states

```text
observation -> candidate -> trusted -> deprecated
```

A single model output is an observation only.

## Promotion

Promote a pattern only when it has repeated observations, acceptable validation success, and no contradictory evidence. Record observation count, success rate, last-seen time, and scope.

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

Those changes require normal implementation, verification, and review.

## Learning targets

Prefer learning:

- routing accuracy
- useful context sources
- verification effectiveness
- common failure modes
- repository-specific conventions
- successful repair strategies
- token/tool efficiency

Do not optimize for raw speed if it reduces correctness or verification quality.
