# Development Hardening Loop

This document describes a maintainer-only method for improving the harness itself.

It is NOT a runtime policy and must never cause normal coding tasks to execute repeated autonomous cycles.

## Purpose

During repository hardening, maintainers may review the system through up to 500 improvement cycles. Each cycle is an external engineering review of the repository, not a loop executed by the shipped harness.

The review method is:

```text
Inspect -> Hypothesize -> Change -> Verify -> Review -> Measure -> Repeat
```

The 500-cycle ceiling is a review budget, not an application execution setting.

## Runtime rule

Normal task execution is a single adaptive run:

```text
Route -> Context -> Select capabilities -> Execute -> Verify -> Review -> Repair if needed -> Learn
```

The harness must not recursively invoke itself or create an unbounded improvement loop unless the user explicitly requests a looped workflow for that task.

## Hardening discipline

Each maintainer review cycle must have a distinct objective, new evidence, and a measurable reason for the change. Repeated identical findings or changes should be consolidated rather than duplicated.

Stop hardening when:

- the identified problem is fixed and verified;
- further changes are cosmetic or speculative;
- remaining work requires product or architectural judgment outside the harness scope;
- regression risk exceeds the expected benefit.

## Safety

The hardening loop must never modify provider permissions, security policy, or external integrations without normal review and validation.
