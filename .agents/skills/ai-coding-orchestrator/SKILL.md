---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for precise task execution, evidence-based RCA, minimal safe changes, verification, collaboration and bounded learning.
---

# Adaptive AI Coding Orchestrator

Lifecycle: `Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Graph/Loop Execute -> Verify -> Review -> Repair if justified -> Evaluate -> Learn -> Stop`.

Normal mode is one adaptive run. Never self-loop unless the user explicitly requests a bounded loop.

## Agent -> Loop -> Graph -> Orchestration

Treat the execution object as progressively more explicit:

1. **Agent:** use a provider for a bounded engineering action.
2. **Loop:** plan, act, observe and evaluate; repair only when new evidence or a changed strategy justifies it.
3. **Graph:** compose agentic nodes with deterministic functions, evaluators, routers, joins and human checkpoints using explicit dependencies.
4. **Orchestration:** own scheduling, budgets, policy, evidence, replay, failure propagation and learning boundaries.

The graph does not replace the agent loop. An agentic graph node may contain a local bounded loop. Do not turn every task into a multi-agent workflow: use the smallest execution topology that improves the verified outcome.

Use `portable/orchestration.py` as the provider-neutral reference implementation. Provider adapters execute model/tool work; AER remains responsible for control-plane invariants.

## Task contract

Create or load a protected contract:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.

Carry the intent digest through phases, retries, graph branches, resumes and handoffs. Nearby findings are deferred. Challenge ambiguity when it materially affects correctness, safety, architecture, scope or verification; otherwise state assumptions and continue.

## Repository-first engineering

Read repository/team instructions, git state, structure, dependencies and tests before editing. Reuse local architecture, naming, placement, exception handling, logging, telemetry, DI, configuration and test patterns. Make the smallest safe change. Do not add speculative abstractions, unrelated cleanup or silent dependencies.

Treat undocumented legacy behavior as protected until evidence says otherwise. Trace callers, branches, feature/config gates, persistence, integrations, failure paths and data shapes. Prefer characterization tests and seam-level compatibility changes over rewrites.

Apply proportionally: DRY, YAGNI, KISS, SOLID, dependency inversion, high cohesion/low coupling, composition, least surprise, least privilege, locality of change, observability, reversibility and evidence over assumption.

## Capability planning and collaboration

Before provider execution, use the deterministic capability catalog and record `capability-plan.json`. Select only justified roles: planner, explorer, researcher, builder, verifier, reviewer, security reviewer or RCA investigator.

Each role has a responsibility, mutation policy, parallel-safety rule and report contract. Parallelize only independent read-only work; never parallelize edits to the same file.

Meaningful handoffs contain `intent_digest + source + destination + phase + findings + decisions + open risks + next actions`. Validate intent and scope before consuming a handoff. Share evidence through the collaboration graph rather than replaying full transcripts.

## Graph execution rules

- Every node has an explicit identity, kind, dependency set and mutation boundary.
- Reject dependency cycles before execution.
- Use deterministic ordering when multiple nodes are ready; parallelize only independent read-only work.
- Bound node retries and total run attempts.
- Evaluate node output before treating it as progress.
- Propagate critical failures instead of allowing downstream work to create false confidence.
- Keep routers subject to the same policy, approval and security gates as ordinary nodes.
- Preserve enough state to replay the decision path without repeating irreversible actions.

## RCA mode

If asked for RCA, diagnosis or investigation without an explicit fix request: do not edit, commit, push or patch. Trace the real call/data flow, inspect source/tests/history/logs/persistence/integrations, compare data shapes, classify `Fact | Inference | Unknown | Recommendation`, attach evidence, record contradictions, and report root cause as `proven | probable | unproven`.

A later regression must link to the original run and intent and become a learning event, not an unsolicited patch.

## Verification and quality

Verification outranks model confidence. Check acceptance, relevant regression paths, final diff and repository-native validation. Never claim tests, commands or absence of regressions that were not observed.

Review weak architectural boundaries, separation of concerns, coupling, data-model invariants/lifecycle/compatibility, failure handling, operational discipline and observability. Consider timeout, retry, cancellation, idempotency, cleanup, configuration, migration, rollout/rollback, logging, metrics, tracing and health requirements when relevant.

## Evaluation loop

For substantive changes, use:

`Generation -> Evaluation -> Repair -> Evaluation -> Stop`.

Evaluation should prefer deterministic tests, repository-native checks and independent review. A failed evaluation must change evidence, diagnosis, strategy, context or tool selection before another attempt. Stop when quality is sufficient, no measurable improvement remains, the budget is exhausted, or regression risk rises.

## Execution and durability

Split substantial work into independently verifiable chunks. Checkpoint meaningful phases/chunks and re-anchor on context rot, instruction loss, intent drift, scope drift or contradiction. Every retry must add evidence or change strategy.

Runtime events are mirrored to `execution.journal.jsonl` as append-only hash-chained records. The journal is separate from checkpoints, telemetry and the final manifest and supports integrity checks, replay projections and future replay-driven evaluation. Journal failure is non-fatal.

## Context economics

Treat the repository as structured evidence. Prefer repository rules/acceptance, AST/symbol/dependency structure, graph impact paths, exact search, semantic retrieval when configured, targeted reads, then verification output.

Use Graphify, code-mem and other extensions only when available, relevant and permitted. Apply the FlashAttention-inspired operational principle: keep stable context small, rank evidence, compact history by information value, preserve proof-bearing state, reuse summaries and avoid transcript replay. Optimize verified outcome per token, call, retry and latency.

## Engineering State Ledger

For non-trivial work maintain:
`INTENT | CONTRACT | REPO_FACTS | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Material decisions reference evidence. Verification identifies proof. Outcome records accepted/rejected/partial results, review/production feedback, regressions and metrics.

## Learning and self-improvement

Use the closed loop:

`Observe -> Outcome -> Candidate -> Regression Replay -> Safety Evaluation -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Record evidence-backed outcomes, reviewer findings, retries, regressions and DO/DON'T lessons. Promote patterns only after repeated evidence and evaluation. Learned advice may improve retrieval and recommendations but never silently rewrites executable behavior, permissions or security policy. Skill and orchestration changes remain proposals until regression and safety gates pass.

A model suggestion is not evidence of improvement. A promoted change must have a before/after comparison against a known-good regression corpus and an auditable promotion decision.

## Optional extensions

Extensions are capabilities, never dependencies. Detect first; use only when available, healthy, relevant and permitted; never install or modify them automatically.

Graphify/code-mem: structural and graph evidence. Superpowers: planning/TDD/debugging. Ponytail: minimal-change/regression checks. Caveman: compact context. LSP: optional diagnostics from an existing suitable server. Sandboxing: explicit future execution boundary; never silently enabled.

Precedence: `Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion

Report: `Outcome | Changed files | Evidence | Verification | Regression checks | Review | Capability plan | Extensions | Assumptions | Risks | Incomplete checks | Efficiency`.

Policies: `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md`, `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`, `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `QUALITY_GOVERNANCE.md`.
