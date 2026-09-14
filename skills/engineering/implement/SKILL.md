---
name: implement
description: Implement an approved spec or ticket with vertical slices, repository-native verification, and review gates.
---

# Implement

Implementation is controlled execution, not planning by trial and error.

## Inputs

Start from an approved request, spec, or agent-ready ticket. Read repository instructions, acceptance criteria, dependencies, and impacted symbols. Acquire fresh `ContextEvidence` before changing code.

## Execution

1. Select the smallest ready work unit.
2. Identify a public behavioral seam.
3. Use `tdd` for the first slice when test infrastructure can observe the behavior.
4. Implement the minimum change.
5. Verify immediately and record evidence.
6. Repeat only for the next bounded slice.
7. Run the full relevant regression set.
8. Run `code-review` before considering the artifact ready.

For repeated repair/research/test passes, use the canonical bounded loop implementation. Its `LoopRunReceipt` and provenance events are part of the same evidence chain as verification and rollout; do not build a second loop engine here.

## Dependencies

Do not start blocked work. Preserve blocking edges in the existing task/decomposition model. Mutating work must respect resource conflicts and the host's permission boundaries.

## Completion

A unit is complete only when acceptance checks pass, regression evidence exists, material review findings are resolved, and the artifact can proceed through the existing rollout lifecycle. State remaining uncertainty explicitly.
