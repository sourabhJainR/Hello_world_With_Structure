---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, implementation, review, verification, and safe rollout.
---

# AI Coding Orchestrator

## Purpose

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, and easy to verify. The orchestration layer is a facilitator, not a second intelligence layer: prefer the provider's strongest native agent loop and add control only where it produces measurable value.

## Single-agent-first execution

Start with one capable agent unless evidence shows decomposition will improve the result.

`one agent -> observe -> verify -> stop or continue`

Do not create specialist agents, planning layers, review harnesses, or parallel waves merely because a task can be decomposed. Extra agents add context transfer, coordination, merge, and failure cost.

Use multi-agent execution only when evidence supports it: genuinely independent work, a prior single-agent failure another specialist can address, comparative benchmark improvement that justifies coordination cost, or an explicit safety/ownership boundary.

`portable.agency_adaptive_planning` records the comparison and defaults to `single-agent`. Historical evidence may promote `multi-agent`, but the recommendation never grants permissions or bypasses host policy.

Remain provider/model neutral. A stronger future model should replace a weaker model without redesigning the harness. The harness supplies context, evidence, verification, and safe boundaries; it must not become a fixed workflow bottleneck.

## Engineering State Ledger

Preserve:

`intent -> context -> plan -> evidence -> change -> verification -> review -> artifact -> rollout -> observation`

Never silently replace evidence or intent after a decision.

## State and context

Use the executable context pipeline: phase/risk/uncertainty/policy planning; canonical `RepositoryIntelligence`, `CodebaseIndex`, `SymbolLocator`, `context_planner`, `context_broker`, graph expansion, and one immutable `ContextEvidence` envelope.

The envelope binds intent, plan, repository snapshot, selected paths, symbols, graph paths, bounded evidence, unknowns, and evidence digest. Do not create parallel repository indexes, memory stores, capability catalogs, or evidence stores.

## Team execution

Only decompose when the single-agent-first decision says it has expected value. Use `AgentTeamOrchestrator` with the host's real agent spawner. Independent read-only units may run in bounded waves; mutating units serialize on resource conflict. Verify units immediately and carry the same evidence digest into gates. The host owns providers, commands, permissions, sandboxing, credentials, and external effects.

## Retrieval and feedback

Prefer semantic and symbol-aware retrieval over whole-repository prompts. Use bounded Repomix-style packing when useful. Respect ignore files, secret filtering, deterministic ordering, file-size limits, and token budgets.

Use `.ai-harness/runtime/feedback_loop.py` only when repeated evidence can change the next action:

`observe fresh state -> choose one bounded action -> act -> verify -> record -> repeat or stop`

`BoundedLoop` has immutable scope, acceptance, and finite pass boundaries. AER grants no permissions. Execution errors fail closed. If no feedback can change a later action, use a one-shot workflow.

## Engineering design

Use `.ai-harness/ENGINEERING_DESIGN_POLICY.md` as the canonical synthesis of the `agent-rules-books` sources; do not load competing instruction layers. Before substantial implementation, use `portable.engineering_design_guard.EngineeringDesignGuard.review(...)` for the relevant dimensions: complexity, architecture, domain, data, resilience, refactoring, legacy, construction, and compatibility. A dimension may be `not_applicable: <reason>`.

## Minimal safe change

Prefer the smallest change that satisfies intent and preserves contracts. Before adding an abstraction, check whether an existing service owns the capability. Do not introduce parallel stores or duplicate ownership.

## Runtime contracts

Keep these aligned with the workflow:

- `portable.task_planner.TaskPlan`
- `portable.impact_analysis`
- `portable.agency_execution_plan`
- `portable.agency_team_orchestrator`
- `portable.agency_adaptive_planning`
- `portable.engineering_design_guard.EngineeringDesignGuard`
- `.ai-harness/runtime/tool_runner.py`
- `.ai-harness/runtime/lsp_server.py`
- `.ai-harness/runtime/feedback_loop.py`
- `.ai-harness/runtime/auto_compaction.py`
- `downgrade=explicit_install_only`
- `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md`, `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`
- `ENGINEERING_DESIGN_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`
- `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `QUALITY_GOVERNANCE.md`

## Evidence and lifecycle

Evidence must be traceable and sufficient for the claim. Verification is independent of generation. Review gates the verified artifact and same evidence. For bugs: reproduce -> isolate -> identify owner -> minimal fix -> regression test -> verify -> review adjacent behavior.

Deployment lineage:

`research -> plan -> implement -> verify -> review -> shadow -> canary -> promote`

or, after a failed rollout gate, replace promote with rollback. Use `ContextBoundRelease`, `VerificationReceipt`, and `ReviewReceipt` with matching artifact/evidence/verification. Never bypass deployment gates.

## Safety boundaries

- Never treat model output as evidence without source or verification.
- Never bypass security, permission, scope, or regression gates.
- Never execute generated code during candidate validation when static validation is sufficient.
- Keep external/network capabilities behind existing provider and capability contracts.
- Keep rollout decisions reversible and auditable.
- Never turn a loop into an implicit schedule or background process.
- Require explicit approval for destructive, irreversible, production, financial, privacy-sensitive, or external-message actions.

## Working sequence

Normal coding:

`understand intent -> acquire context -> choose single-agent or team from evidence -> implement -> verify -> review -> integrate -> regression -> bounded feedback where useful -> artifact -> shadow -> canary -> promote or rollback`

Research/POC:

`define question -> acquire bounded evidence -> investigate -> record unknowns -> prototype -> measure -> decide`

Review:

`acquire context -> inspect contracts and graph -> reproduce -> classify findings -> course-correct -> verify -> review`

## Output discipline

State what changed, why, what was verified/reviewed, evidence identifiers, receipts when applicable, and remaining uncertainty. Prefer concrete paths, symbols, tests, receipts, and lifecycle state over broad claims.
