---
name: engineering-router
description: Route engineering work to the smallest appropriate repository-native skill flow.
disable-model-invocation: true
---

# Engineering Router

Use the existing AI Coding Orchestrator as the execution authority. This skill only chooses the path; it never creates a competing runtime, memory store, or evidence ledger.

## Main flow

For a non-trivial change:

1. `grill-with-docs` when intent, terminology, scope, or acceptance criteria are still fuzzy.
2. `research` when an unfamiliar technology, dependency, architecture or design decision needs evidence before implementation.
3. `to-spec` when the work spans sessions or needs a durable build contract.
4. `to-tickets` when the spec decomposes into independently verifiable units with dependencies.
5. `prototype` when a bounded runnable experiment can resolve uncertainty faster than production implementation.
6. `implement` for controlled production changes. `implement` drives `tdd` where a behavioral seam exists and closes with `code-review`.
7. `verify -> review -> artifact -> rollout` using the existing orchestration and provenance contracts.
8. `retro` after a meaningful implementation/debugging session when the user wants environment improvements from observed evidence.

## On-ramps

- Broken behavior -> `diagnosing-bugs`.
- Active merge/rebase conflicts -> `resolving-merge-conflicts`.
- Design or module-shape uncertainty -> `codebase-design`.
- Codebase health -> `improve-codebase-architecture`.
- Domain vocabulary uncertainty -> `domain-modeling`.
- User explicitly asks for test-first implementation -> `tdd`.
- User asks to review a change -> `code-review`.
- User asks what should improve after a session -> `retro`.

## Rules

Keep the selected flow bounded. Carry the existing intent, context evidence, artifact, verification, and provenance identifiers through every handoff. Do not introduce a parallel planning, memory, repository graph, or receipt abstraction.

When work crosses a phase boundary, prefer continue when context is still load-bearing; otherwise use the repository's existing compaction/handoff mechanisms.

## Existing ownership

- Execution authority: `skills/ai-coding-orchestrator/SKILL.md`
- Context authority: `.ai-harness` context pipeline and `ContextEvidence`
- Repository intelligence authority: canonical `CodebaseIndex` / `RepositoryIntelligence`
- Loop authority: `.ai-harness/runtime/feedback_loop.py`
- Provenance authority: existing provenance ledger
- Release authority: existing release/rollout contracts
