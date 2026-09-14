---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, POC, investigation, implementation, review, bug fixing, tests, verification, and safe artifact rollout.
---

# AI Coding Orchestrator

## Purpose

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, and easy to verify. The orchestrator is for research, POC, investigation, coding, review, bug fixes, unit-test writing, and deployment validation.

## Engineering State Ledger

Every turn should preserve:

`intent -> context -> plan -> evidence -> change -> verification -> review -> artifact -> rollout -> observation`

Carry stable identifiers across stages. Never silently replace evidence or intent after a decision has been made.

## Context acquisition

Use the executable context pipeline: plan retrieval from phase/risk/uncertainty/policy, use canonical `RepositoryIntelligence` and `CodebaseIndex`, resolve symbols with `SymbolLocator`, expand relevant graph relationships, rank and budget evidence with `context_planner`, lease selected records through `context_broker`, and return one immutable `ContextEvidence` envelope.

The envelope contains intent, context-plan, repository snapshot, selected paths, symbol references, graph paths, bounded evidence items, unknowns, and an evidence digest.

Do not create a second repository index, memory store, capability catalog, or evidence store. Compatibility layers must delegate to the canonical implementation.

## Repository-aware retrieval

For code tasks prefer semantic and symbol-aware retrieval over whole-repository prompts. Use graph expansion for callers, callees, interfaces, tests, configuration, and impacted files. Use Repomix-inspired packing only when a bounded repository snapshot is useful. Respect `.gitignore`, `.ignore`, `.repomixignore`, secret filtering, deterministic ordering, file-size limits, and token budgets.

A semantic address uses `relative/path::Symbol`. Snapshot digests are validity boundaries: refresh the index after repository mutation and acquire a new context envelope when fresh evidence is required.

## Team decomposition and early gates

For substantial work, split the request into complete `WorkUnit`s with explicit goals, dependencies, specialist roles, read/write resources, and mutation mode. Use `AgentTeamOrchestrator` with the host's real agent spawner. Independent read-only units may run in bounded parallel waves; mutating units are serialized by resource conflict.

Do not wait until the end to discover a bad approach. After each unit completes, run verification immediately and then independent review. A failed verification/review blocks that unit and its dependents so later agents do not spend tokens on work that is already invalid. Carry the same `ContextEvidence.evidence_digest` into every spawned unit and gate.

The host remains authoritative for model/provider selection, commands, permissions, sandboxing, credentials, and external side effects.

## Minimal safe change

Prefer the smallest change that satisfies the intent and preserves existing contracts. Before adding a new abstraction, check whether an existing service already owns the capability. Prefer Adapter, Strategy / Policy, State Machine, Pipeline, and Dependency Injection patterns when they fit the existing topology.

Do not introduce parallel stores or duplicate ownership merely to support a new feature. Extend the canonical path and add a compatibility adapter when older callers need it.

## Existing runtime contracts

Keep these established runtime entry points aligned with the orchestration workflow:

- `portable.task_planner.TaskPlan`
- `portable.impact_analysis`
- `portable.agency_execution_plan`
- `portable.agency_team_orchestrator`
- `.ai-harness/runtime/tool_runner.py`
- `.ai-harness/runtime/lsp_server.py`
- `.ai-harness/runtime/feedback_loop.py`
- `.ai-harness/runtime/auto_compaction.py`
- `downgrade=explicit_install_only`
- `ORCHESTRATION_SPEC.md`

## Evidence, verification, and review

Evidence must be traceable to a source, bounded by the context plan, and sufficient for the claim. Verification is independent of generation. Review is a first-class gate, not a prose-only final check: it must evaluate the verified artifact against the same evidence and leave no unresolved material findings before rollout.

For bugs: reproduce -> isolate -> identify owner -> make minimal fix -> add regression test -> verify -> review adjacent behavior.

For review: inspect contract, data flow, ownership, failure paths, security boundaries, concurrency, observability, and tests. Report findings with evidence and impact. Course-correct before dependent work continues.

## Deployment lifecycle

The same immutable `ContextEvidence` lineage must flow from research through deployment. The executable sequence is:

`research -> plan -> implement -> verify -> review -> shadow -> canary -> promote`

or, on a failed rollout gate/observation:

`research -> plan -> implement -> verify -> review -> shadow -> canary -> rollback`

Use `ContextBoundRelease`. Verification creates a `VerificationReceipt`; review creates a `ReviewReceipt` bound to the same artifact, evidence, and verification. Shadow and canary require that review. Promotion requires matching verification and review receipts and the same artifact already in canary. Release history records evidence, verification, and review digests.

If the repository changes and fresh verification is required, acquire a new envelope rather than mutating the old one.

## Safety boundaries

- Never treat model output as evidence without a source or verification result.
- Never bypass security, permission, scope, or regression gates because a task is urgent.
- Never execute generated code during candidate validation when static validation is sufficient.
- Keep external/network capabilities behind the existing provider and capability contracts.
- Keep rollout decisions reversible and auditable.

## Working sequence

For normal coding:

`understand intent -> acquire context -> decompose -> implement units -> early verify/review -> integrate -> regression -> artifact -> shadow -> canary -> promote or rollback`

For research/POC:

`define question -> acquire bounded evidence -> investigate -> record unknowns -> prototype -> measure -> decide`

For review:

`acquire context -> inspect contracts and graph -> reproduce where needed -> classify findings -> course-correct -> verify -> review`

## Output discipline

State what changed, why, what was verified, what was reviewed, evidence identifiers, and remaining uncertainty. Prefer concrete file paths, symbols, tests, receipts, and lifecycle state over broad claims.
