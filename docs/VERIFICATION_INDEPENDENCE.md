# Verification Independence

Verification is an evidence-producing activity, not a formality after implementation.

## Verification hierarchy

Choose the cheapest evidence that can prove the acceptance criterion, then add stronger evidence when risk requires it:

1. focused unit/property tests
2. integration/contract tests
3. build/type/lint/static analysis
4. realistic workflow or sandbox execution
5. independent review
6. production-like evidence when explicitly permitted

## Author/reviewer separation

For meaningful or high-risk changes, prefer a fresh reviewer context. Give it:

- the original acceptance criteria
- the final diff
- relevant architecture/evidence
- required verification expectations

Do not give it the author's entire reasoning transcript unless needed to understand an unresolved fact.

## Anti-false-positive checks

The verifier must look for tests that can pass while the requested behavior is still broken. Consider:

- testing the wrong layer
- asserting implementation details instead of behavior
- only testing the happy path
- mocking away the failure under investigation
- testing newly written code with assumptions copied from that code
- ignoring compatibility or downstream effects

## Completion rule

A passing test suite is not sufficient if it does not prove the requested behavior. Conversely, do not run broad checks that add cost without increasing confidence for the current risk.

Record verification evidence with the final outcome so a later session can trust the result without replaying the entire investigation.
