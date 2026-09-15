---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, implementation, review, verification, visual documentation, and safe rollout.
---

# AI Coding Orchestrator

## Purpose

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, and easy to verify. The orchestration layer is a facilitator, not a second intelligence layer.

## Repository map first

Before broad repository reading, prefer the dependency-free repository map for structural, cross-file, unfamiliar, or risk-sensitive tasks:

```bash
python -m portable.repo_intelligence . --for="<task>" --token-budget=4000
```

Focused questions:

```bash
python -m portable.repo_intelligence . --mode=callers --symbol="<symbol>"
python -m portable.repo_intelligence . --mode=callees --symbol="<symbol>"
python -m portable.repo_intelligence . --mode=impact --symbol="<symbol>" --graph-depth=1
python -m portable.repo_intelligence . --mode=tests --symbol="<symbol>"
python -m portable.repo_intelligence . --mode=situ --base=HEAD
```

The map is a bounded evidence accelerator, not a proof oracle. Its output carries a stable snapshot digest, confidence on graph edges, skipped-file inventory, parse-error disclosure, and explicit unknowns. A zero result means no evidence was found, not that the thing does not exist. Candidate test relationships are not proof of execution coverage.

Use the detail ladder:

`map -> ranked files/symbols -> signatures/windows -> full bodies only for selected items`

If the map cannot answer a question completely, preserve its unknowns and acquire the smallest additional evidence needed.

## Single-agent-first execution

Start with one capable agent unless evidence shows decomposition will improve the result.

`one agent -> observe -> verify -> stop or continue`

Use multi-agent execution only for genuinely independent work, a prior failure another specialist can address, measurable benchmark improvement that justifies coordination cost, or an explicit safety/ownership boundary.

Remain provider/model neutral. The harness supplies context, evidence, verification, and safe boundaries.

## Engineering State Ledger

Preserve:

`intent -> context -> plan -> evidence -> change -> verification -> review -> artifact -> rollout -> observation`

Never silently replace evidence or intent after a decision.

## State and context

Use the canonical `RepositoryIntelligence`, `CodebaseIndex`, `SymbolLocator`, context planning, graph expansion, and immutable `ContextEvidence` envelope. Do not create parallel repository indexes, memory stores, capability catalogs, or evidence stores.

The envelope binds intent, plan, repository snapshot, selected paths, symbols, graph paths, bounded evidence, unknowns, and evidence digest.

## Team execution

Only decompose when the single-agent-first decision says it has expected value. Independent read-only units may run in bounded waves; mutating units serialize on resource conflict. Carry the same evidence digest into verification gates.

## Retrieval and feedback

Prefer semantic and symbol-aware retrieval over whole-repository prompts. Use bounded deterministic packing when useful. Respect ignore files, secret filtering, deterministic ordering, file-size limits, and token budgets.

Use `.ai-harness/runtime/feedback_loop.py` only when repeated evidence can change the next action:

`observe fresh state -> choose one bounded action -> act -> verify -> record -> repeat or stop`

## Engineering design

Use `.ai-harness/ENGINEERING_DESIGN_POLICY.md` as the canonical synthesis of engineering design sources. Before substantial implementation, use `portable.engineering_design_guard.EngineeringDesignGuard.review(...)` for relevant dimensions.

## Skill composition

- Use `research` for evidence acquisition before implementation when uncertainty is external, architectural or technological.
- Use `prototype` when a bounded experiment can resolve uncertainty faster than production implementation.
- Use `resolving-merge-conflicts` only for an active merge/rebase conflict; it must preserve intent and end with verification.
- Use `interactive-documentation` when architecture, workflow, sequence, data-flow, or lifecycle evidence needs a portable visual HTML artifact.
- Use `retro` after meaningful sessions to convert observed failures into small, durable environment improvements.

These skills are orchestration surfaces. They reuse the canonical repository/context/evidence/provenance stores and never create parallel ownership.

## Minimal safe change

Prefer the smallest change that satisfies intent and preserves contracts. Do not introduce parallel stores or duplicate ownership.

## Runtime contracts

Keep these aligned with the workflow:

- `portable.task_planner.TaskPlan`
- `portable.repo_intelligence.RepositoryMap`
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

or, after a failed rollout gate, rollback. Never bypass deployment gates.

## Safety boundaries

- Never treat model output as evidence without source or verification.
- Never bypass security, permission, scope, or regression gates.
- Keep external/network capabilities behind existing provider and capability contracts.
- Keep rollout decisions reversible and auditable.
- Require explicit approval for destructive, irreversible, production, financial, privacy-sensitive, or external-message actions.

## Working sequence

Normal coding:

`understand intent -> repository map -> acquire bounded context -> choose single-agent or team from evidence -> implement -> verify -> review -> integrate -> regression -> bounded feedback where useful -> artifact -> shadow -> canary -> promote or rollback`

Research/POC:

`define question -> acquire bounded evidence -> research -> prototype when useful -> measure -> decide -> record unknowns -> implement through normal gates`

Visual documentation:

`define audience -> repository map -> context/evidence -> author typed topology -> validate -> render standalone HTML -> inspect -> publish/share`

Review:

`acquire context -> inspect contracts and graph -> reproduce -> classify findings -> course-correct -> verify -> review`

## Output discipline

State what changed, why, what was verified/reviewed, evidence identifiers, receipts when applicable, and remaining uncertainty. Prefer concrete paths, symbols, tests, receipts, graph edges, snapshot digests, and lifecycle state over broad claims.
