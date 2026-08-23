# Repository AI Agent Instructions

This file is the shared durable instruction surface for AI coding agents.

## Mission

Use the repository's AI harness under `.ai-harness/` for structured work when practical.

## Before changing code

1. Inspect the relevant repository structure and existing patterns.
2. Read applicable instructions under `.ai-harness/`.
3. Build a focused understanding of the smallest set of files needed.
4. State assumptions when requirements are incomplete.

## Capability routing

Use capabilities only when useful:

- `research`: unknown technology, external dependency, competing approaches, current facts, or architecture decisions.
- `poc`: feasibility or technical uncertainty that should be tested before production implementation.
- `grill`: high-risk design, security, performance, migration, or important production changes that benefit from adversarial review.
- `review`: normal code-quality and regression review.

Do not run optional capabilities by default for trivial changes.

## Coding rules

- Keep changes focused.
- Reuse existing abstractions and dependencies.
- Preserve compatibility unless the task says otherwise.
- Do not modify unrelated files.
- Add or update tests where appropriate.
- Never claim a command was run unless it was run and its result is known.

## Completion

Report:

- What changed
- Files changed
- Validation performed
- Important assumptions
- Remaining risks or follow-up work
