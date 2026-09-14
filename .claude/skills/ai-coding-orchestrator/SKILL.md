---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, POC, investigation, implementation, review, bug fixing, tests, verification, and safe artifact rollout.
---

# AI Coding Orchestrator

## Purpose

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, and easy to verify. The orchestrator is for research, POC, investigation, coding, review, bug fixes, unit-test writing, and deployment validation.

## Engineering State Ledger

Every turn should preserve:

`intent -> context -> plan -> evidence -> change -> verification -> artifact -> rollout -> observation`

Carry stable identifiers across stages. Never silently replace evidence or intent after a decision has been made.

## Context acquisition

Use the executable context pipeline:

1. plan retrieval from phase, risk, uncertainty, and policy
2. use canonical `RepositoryIntelligence` and `CodebaseIndex`
3. resolve symbols with `SymbolLocator`
4. expand relevant graph relationships
5. rank and budget evidence with `context_planner`
6. lease selected records through `context_broker`
7. return one immutable `ContextEvidence` envelope

The envelope contains intent, context-plan, repository snapshot, selected paths, symbol references, graph paths, bounded evidence items, unknowns, and an evidence digest.

Do not create a second repository index, memory store, capability catalog, or evidence store. Compatibility layers must delegate to the canonical implementation.

## Repository-aware retrieval

For code tasks prefer semantic and symbol-aware retrieval over whole-repository prompts. Use graph expansion for callers, callees, interfaces, tests, configuration, and impacted files. Use Repomix-inspired packing only when a bounded repository snapshot is useful. Respect `.gitignore`, `.ignore`, `.repomixignore`, secret filtering, deterministic ordering, file-size limits, and token budgets.

A semantic address uses `relative/path::Symbol`. Snapshot digests are validity boundaries: refresh the index after repository mutation and acquire a new context envelope when fresh evidence is required.

## Minimal safe change

Prefer the smallest change that satisfies the intent and preserves existing contracts. Before adding a new abstraction, check whether an existing service already owns the capability. Prefer Adapter, Strategy / Policy, State Machine, Pipeline, and Dependency Injection patterns when they fit the existing topology.

Do not introduce parallel stores or duplicate ownership merely to support a new feature. Extend the canonical path and add a compatibility adapter when older callers need it.

## Evidence and verification

Evidence must be traceable to a source, bounded by the context plan, and sufficient for the claim. Verification is independent of generation. For implementation tasks, cover changed behavior with focused unit tests and run the relevant existing regression suite.

For bugs: reproduce -> isolate -> identify owner -> make minimal fix -> add regression test -> verify adjacent behavior.

For review: inspect contract, data flow, ownership, failure paths, security boundaries, concurrency, observability, and tests. Report findings with evidence and impact.

## Deployment lifecycle

The same `ContextEvidence` object must flow into rollout evaluation. Do not reconstruct context between execution and deployment.

`shadow -> canary -> promote`

or

`shadow -> canary -> rollback`

Pass `context_evidence` to shadow/canary evaluation. Each report and staged canary record carries `context_evidence_digest`. Use `ContextBoundRelease` for executable artifact transitions so `shadow`, `canary`, `promote`, and `rollback` carry the same evidence digest into the release audit trail.

Policy records retain the context evidence digest. If the repository changes and fresh verification is required, acquire a new envelope rather than mutating the old one.

## Safety boundaries

- Never treat model output as evidence without a source or verification result.
- Never bypass security, permission, scope, or regression gates because a task is urgent.
- Never execute generated code during candidate validation when static validation is sufficient.
- Keep external/network capabilities behind the existing provider and capability contracts.
- Keep rollout decisions reversible and auditable.

## Working sequence

For a normal coding task:

`understand intent -> acquire context -> plan -> implement -> test -> review -> verify -> package -> shadow/canary -> promote or rollback`

For research/POC:

`define question -> acquire bounded evidence -> investigate -> record unknowns -> prototype -> measure -> decide`

For review:

`acquire context -> inspect contracts and graph -> reproduce where needed -> classify findings -> propose minimal safe change -> verify`

## Output discipline

State what changed, why, what was verified, and any remaining uncertainty. Prefer concrete file paths, symbols, tests, evidence identifiers, and lifecycle state over broad claims.
