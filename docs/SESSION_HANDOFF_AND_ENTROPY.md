# Session Handoff and Repository Entropy Policy

Long-running agent sessions must not preserve context at the expense of clarity.

## Handoff contract

When a task crosses a context boundary, persist only durable state:

```text
TASK: one-sentence outcome
CONTRACT: acceptance criteria and constraints
DONE: verified completed work
OPEN: unresolved work
EVIDENCE: tests/review/results
RISKS: known uncertainty or regressions
NEXT: one concrete next action
```

Do not copy the full transcript, tool output, source files, or reasoning into the handoff.

A new session must rehydrate missing evidence from the repository rather than trusting an old narrative.

## Fresh-context review

For material changes, a reviewer should receive the task contract, diff, relevant evidence, and verification requirements, but not unnecessary implementation history. This reduces confirmation bias and makes the reviewer test the intended behavior rather than the author's path.

## Entropy check

After a long or multi-file task, inspect only the affected change surface for:

- stale documentation
- contradictory comments or examples
- dead code introduced by the change
- obsolete tests
- temporary files
- duplicate implementations
- unresolved merge artifacts
- changed APIs with stale callers/docs

Do not launch a repository-wide cleanup unless requested.

## Stop conditions

A session should stop when the acceptance contract is satisfied and verification evidence is sufficient. More agent activity is not automatically better.

Continue only when:

- a required check failed
- evidence contradicts the implementation
- an acceptance criterion remains unresolved
- a material risk is still unexplored

Every retry must state what new evidence or changed approach justifies it.
