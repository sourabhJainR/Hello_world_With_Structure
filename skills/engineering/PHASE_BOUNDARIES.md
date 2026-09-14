---
name: phase-boundaries
description: Choose safe transitions between engineering phases without introducing another state or memory system.
---

# Phase Boundaries

A phase is a bounded unit such as discovery, design, implementation, verification, review, or rollout.

At each boundary choose exactly one transition:

1. **Continue** when the current context contains load-bearing evidence needed by the next phase.
2. **Clear** when the next phase can reacquire everything it needs from repository state and durable evidence.
3. **Handoff** when work moves to a new directory, harness, colleague, prototype, or side task and a portable artifact is required.
4. **Subagent** when the next activity is independent, bounded, read-only, or otherwise benefits from a separate context window.
5. **Compact** when the work remains one continuous effort but context pressure makes reasoning quality unsafe.

## Decision order

Ask in order:

- Does the next phase depend on unresolved reasoning in this context? If yes, continue.
- Can the next phase be reconstructed from durable repository evidence? If yes, clear.
- Is the work crossing an ownership or workspace boundary? If yes, handoff.
- Is the work independently executable and bounded? If yes, subagent.
- Is context pressure the only problem? If yes, compact.

## Handoff contract

A handoff is evidence, not authority. The portable artifact MUST contain:

- `intent_digest`
- current phase and requested next phase
- scope and non-goals
- accepted decisions
- known facts with source/evidence IDs
- inferred findings explicitly marked as inferred
- unresolved questions and risks
- current repository snapshot/reference
- relevant artifact IDs and verification/review receipt IDs
- exact next action and stopping condition

The handoff MUST NOT create a second memory store. Put the artifact through the existing repository/context/provenance ownership path.

## Provenance

Every handoff is linked to the same evidence chain as the rest of the execution lifecycle. Record a handoff event through the existing provenance ledger when the runtime supports it. Preserve `intent_digest`, context evidence digest, parent provenance hash, and artifact digest.

A handoff does not authorize execution. The receiving phase must reacquire or validate fresh context when the repository has changed.

## Context hygiene

Do not clear or compact merely because a phase ended. Preserve context when the reasoning itself is load-bearing. Do not carry stale source evidence across mutations; reacquire a new context envelope when freshness matters.

## Failure rules

- Missing or invalid handoff fields block consumption.
- Intent mismatch blocks consumption.
- Scope expansion requires a new decision/specification step.
- Stale repository evidence requires refresh.
- A handoff cannot bypass verification, review, security, approval, or rollout gates.
