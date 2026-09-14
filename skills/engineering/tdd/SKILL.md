---
name: tdd
description: Test-first development for new behavior and bug fixes at stable public seams.
---

# Test-Driven Development

Use the repository's existing test command, package layout, and public interfaces. Do not invent a parallel test framework.

## Loop

1. Identify one behavioral seam and the acceptance behavior it must prove.
2. Add one failing test that observes the behavior through the public interface.
3. Make the smallest implementation change that turns the test green.
4. Run the focused test, then relevant regression tests.
5. Record verification evidence in the normal run/provenance chain.
6. Repeat one vertical slice at a time.

## Test quality

Prefer behavior over implementation details. Avoid tests that only assert private helpers, internal call order, or duplicated implementation logic. Expected results must come from the requirement, a known-good example, or another independent source of truth.

Keep refactoring outside the red-green step. Refactor only after behavior is green and preserve the same public seam.

## Repository integration

Acquire `ContextEvidence` before broad exploration. Carry its evidence digest through the slice. For repeated passes, use `.ai-harness/runtime/feedback_loop.py`; each bounded loop must emit its normal `LoopRunReceipt` and provenance events.

A failed test is evidence, not permission to widen scope. Stop when the acceptance behavior is proven or when a new dependency/decision requires a fresh plan.
