# Review Policy

Review is a separate evidence-gathering activity, not a confirmation step.

## Review lenses

Use only the lenses relevant to the change:

- correctness
- security
- reliability
- performance
- architecture
- compatibility
- tests
- operability

## Independence

A reviewer should receive the task contract, relevant repository evidence, and actual diff, but not the implementer's conclusions until after forming its own findings.

For high-risk work, use at least two independent lenses and prefer separate provider/model context when practical.

## Finding contract

Each finding must contain:

- severity: blocker | critical | major | minor | advisory
- location
- evidence
- impact
- recommended action
- confidence

Assertions without evidence are not findings.

## Disagreement

Disagreement is useful evidence. The orchestrator should preserve conflicting findings, seek additional evidence, and escalate instead of averaging away a safety concern.

## Completion

Review passes only when no blocker/critical finding remains and all required major findings are resolved or explicitly accepted under policy.
