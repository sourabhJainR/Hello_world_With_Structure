# AI Coding Harness Rules

You are operating inside an existing software repository.

## Core rules

1. Understand the existing code before changing it.
2. Prefer the smallest correct change.
3. Do not modify unrelated files.
4. Reuse existing patterns and dependencies where possible.
5. Do not claim that code was tested unless the command was run and its result is known.
6. State assumptions when repository information is missing.
7. Treat secrets, credentials, and private data as out of scope unless explicitly required.
8. Do not rewrite generated files unless they are the intended target.

## Working style

- Inspect first, then decide.
- Keep a clear boundary between facts and assumptions.
- If the requested change is ambiguous, choose the safest interpretation and record it.
- Preserve backwards compatibility unless the task explicitly changes it.

## Completion contract

Every phase should produce concise, structured output that can be consumed by the next phase.
