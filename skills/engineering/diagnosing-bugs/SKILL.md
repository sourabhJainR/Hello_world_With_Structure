---
name: diagnosing-bugs
description: Diagnose difficult bugs with a tight failing feedback loop, minimal fix, regression test, and provenance-backed verification.
---

# Diagnosing Bugs

Do not start from a theory. Start by making the reported failure reproducible on the current tree.

## Process

1. Pin the bad behavior with one focused command or test that goes red for the reported defect.
2. Acquire bounded `ContextEvidence` and inspect the smallest relevant call/data path.
3. Isolate the owner of the behavior using symbols, callers/callees, configuration, and recent changes.
4. Form one falsifiable hypothesis at a time and test it with the smallest probe.
5. Fix at the owning seam rather than patching downstream symptoms.
6. Add a regression test at the public behavioral seam.
7. Run focused verification, then adjacent regression coverage.
8. Review the changed path and record the outcome in the normal provenance chain.

## Feedback loop

A repeated diagnosis cycle belongs in `.ai-harness/runtime/feedback_loop.py` when each pass can change the next action. Bound the pass count and scope. Never turn diagnosis into autonomous background behavior.

## Stop conditions

Stop when the defect is reproduced, the cause is supported by evidence, the minimal fix is green, and adjacent behavior has been checked. If reproduction cannot be established, report that constraint rather than inventing a fix.
