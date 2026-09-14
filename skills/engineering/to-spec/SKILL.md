---
name: to-spec
description: Turn an agreed engineering conversation into a durable implementation spec tied to repository evidence and acceptance checks.
disable-model-invocation: true
---

# To Spec

Synthesize rather than re-interview. Use the current conversation, repository evidence, existing context documents, and ADRs.

## Spec shape

Capture:

- goal and user-visible outcome
- scope and explicit non-goals
- affected modules/symbols
- behavioral requirements and acceptance checks
- compatibility and migration constraints
- failure/security/observability requirements
- dependencies and blocking decisions
- verification plan
- stopping condition

Every requirement should be testable or externally verifiable. Link claims to existing evidence where possible.

## Ownership

Write the spec only to the repository's existing documentation location. Do not create another planning database. Preserve the same intent and context evidence identifiers when the spec becomes input to implementation.
