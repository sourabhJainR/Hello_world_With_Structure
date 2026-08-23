# Repository AI Agent Instructions

This repository uses an adaptive, provider-neutral AI coding orchestrator.

## Default behavior

For every non-trivial software task, infer the required engineering state from the prompt, task, Jira/issue reference, repository state, risk, uncertainty, and acceptance criteria. Use the minimum safe workflow. Do not make the user choose Research, POC, Grill, Debug, Review, or other capabilities manually unless requested.

Canonical skill:

`.agents/skills/ai-coding-orchestrator/SKILL.md`

Engineering principles:

`.ai-harness/principles.md`

Executable harness:

`python .ai-harness/run.py`

## Automatic capability routing

- research: unknown technology, external facts, competing options, architecture decisions
- poc: feasibility or unresolved technical uncertainty
- debug: failures, regressions, intermittent behavior, root-cause analysis
- grill: meaningful security, migration, performance, production, or high-risk design work
- review: meaningful code changes and release-impacting changes

Skip optional capabilities when repository evidence already makes them unnecessary.

## Language neutrality

Rules must be expressed in terms of behavior, contracts, dependencies, state, data, risk, and architecture rather than syntax or framework names. Adapt the principles to the language and ecosystem already used by the repository.

Do not prescribe interfaces, classes, constructors, modules, packages, async patterns, or dependency-injection frameworks when the language or repository provides a better equivalent. The principle matters; the syntax does not.

## Engineering principles

Apply `.ai-harness/principles.md` proportionally. The core expectations are:

- DRY: avoid duplicated knowledge and inconsistent sources of truth, but do not create abstractions merely to remove small repetition.
- YAGNI: do not build speculative capability or extension points without a current need.
- KISS: prefer the simplest design that satisfies requirements, quality, and scale.
- DI / Dependency Inversion: depend on stable contracts and make volatile external dependencies replaceable where useful for testing, isolation, or changeability.
- SOLID: apply selectively to improve cohesion, coupling, substitutability, focused contracts, and dependency direction; never as a ritual.
- Separation of concerns: keep business rules, orchestration, state, persistence, transport, presentation, and infrastructure appropriately separated.
- High cohesion and low coupling: keep related behavior together and minimize unnecessary cross-component dependencies.
- Composition over inheritance: prefer the simplest collaboration model that preserves clear behavior and substitutability.
- Least knowledge: avoid unnecessary knowledge of collaborator internals.
- Fail fast and explicitly: detect invalid input and violated invariants early.
- Single source of truth: avoid independently maintained duplicate business or configuration knowledge.
- Least surprise: follow repository conventions and predictable behavior.
- Make invalid states hard to represent: use contracts, types, validation, or equivalent mechanisms.
- Compatibility by default: preserve public behavior and integrations unless a breaking change is intentional.
- Test the behavior: prove meaningful behavior, regressions, contracts, and important failure modes.
- Security by default: protect trust boundaries, secrets, permissions, and untrusted input.
- Observability and failure awareness: consider diagnosability, resource use, concurrency, retries, partial failure, cancellation, idempotency, and cleanup when relevant.
- Reversibility: identify rollback or recovery paths for consequential changes.
- Evidence over assumption: prefer tests, repository evidence, specifications, measurements, and verified documentation.
- Locality of change: change the smallest relevant surface area.

When principles conflict, choose based on task scope, compatibility, evidence, performance, reliability, and simplicity. Explain meaningful deviations.

## Context and tokens

Use repository maps and targeted file reads. Carry compact summaries, decisions, failures, and open questions rather than full transcripts. Retrieve only relevant learned memory.

## Learning

Every completed run may contribute evidence-backed lessons to `.ai-harness/memory/`. Lessons are promoted only after repeated successful observations. Never allow one model response to modify harness code or permanent rules automatically.

## Coding rules

- Inspect before changing code.
- Prefer the smallest correct change.
- Reuse existing patterns and dependencies.
- Do not modify unrelated files.
- Add or update focused tests where useful.
- Preserve compatibility unless the task says otherwise.
- Never claim commands, tests, Jira data, or research sources that were not accessed.

## Completion

Report what changed, files changed, validation performed, important assumptions, principles that materially influenced the design, and remaining risks.