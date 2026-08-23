# Verification Policy

Verification is layered and evidence-driven.

## Evidence order

1. Direct acceptance-criteria evidence
2. Focused behavioral tests
3. Build/type/compile validation
4. Integration/system checks
5. Static analysis and linting
6. Diff and structural checks
7. Reviewer findings
8. Model self-report

Lower-ranked evidence never overrides failing higher-ranked evidence.

## Task scorecard

Every implementation should answer:

- What behavior changed?
- How is the requested behavior proven?
- What important failure path is covered?
- What contracts changed?
- What compatibility risk remains?
- What was not tested and why?

## Verification failure

A failed check enters diagnosis, not blind retry. The repair phase must identify the failure, create a new hypothesis, change the approach, and rerun the smallest useful validation before broader validation.

## Acceptance

A run is ACCEPTED only when all mandatory checks pass and there is no unresolved critical/blocking reviewer finding.
