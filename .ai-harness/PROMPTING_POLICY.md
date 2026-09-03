# Prompting Policy

The harness uses a complete-job prompting pattern for provider calls.

## Rules

1. **Give the whole job upfront.** The effective prompt contains task, intent, repository context, constraints, boundaries, acceptance/exit criteria, and the expected response contract before the provider starts.
2. **Interview only for material ambiguity.** If missing information can change the implementation and cannot be established safely from repository evidence, emit `CLARIFICATION_NEEDED` before mutating work. Do not ask questions that repository inspection can answer.
3. **Explain why.** Decisions should preserve the reason behind constraints, not depend on a pile of arbitrary prohibitions.
4. **Define done.** Stop when the task contract, acceptance criteria, and required evidence are satisfied. Interesting adjacent findings remain deferred.
5. **Keep output focused.** Avoid chain-of-thought narration, repeated task statements, and verbose progress reports.
6. **Do not duplicate verification instructions.** The model should use harness evidence and repair failures; deterministic tests, diff checks, security gates, and acceptance evidence remain owned by the control plane.
7. **Preserve auditability.** The canonical prompt remains unchanged. The provider receives a derived effective prompt so the authored request and model-facing instructions can be distinguished.

## Design intent

This policy reduces iteration and token waste while improving autonomous decision quality. It does not weaken the harness's independent verification, review, scope, approval, or staged-change controls.
