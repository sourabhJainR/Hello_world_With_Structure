---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, implementation, review, verification, visual documentation, and safe rollout.
---

# AI Coding Orchestrator

## Purpose

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, compatible, and easy to verify. The orchestrator facilitates work; it does not create a second intelligence or ownership layer.

## Repository map first

For structural, cross-file, unfamiliar, or risk-sensitive tasks, prefer the dependency-free repository map before broad reading:

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

The map is evidence acceleration, not proof. Preserve its snapshot digest, confidence, skipped files, parse errors, and unknowns. Use the detail ladder: `map -> ranked files/symbols -> signatures/windows -> full bodies only for selected items`.

## Single-agent-first

Start with one capable agent: `one agent -> observe -> verify -> stop or continue`. Use multi-agent execution only when independent work, prior failure, measurable benchmark value, or a clear safety/ownership boundary justifies the coordination cost. Remain provider/model neutral.

## Canonical state and context

Preserve the ledger:

`intent -> context -> plan -> evidence -> change -> verification -> review -> artifact -> rollout -> observation`

Use canonical `RepositoryIntelligence`, `CodebaseIndex`, `SymbolLocator`, context planning, graph expansion, and immutable `ContextEvidence`. Do not create parallel repository indexes, memory stores, capability catalogs, evidence stores, or workflow engines.

## Retrieval and feedback

Prefer symbol-aware and semantic retrieval over whole-repository prompts. Use bounded deterministic packing, ignore files, secret filtering, deterministic ordering, file-size limits, and token budgets. Use `.ai-harness/runtime/feedback_loop.py` only when fresh evidence can change the next bounded action.

## Curated change quality

Use `.ai-harness/ENGINEERING_DESIGN_POLICY.md` and `portable.engineering_design_guard.EngineeringDesignGuard.review(...)` for substantial implementation.

For code changes, make this evidence explicit:

`reuse candidates -> usage compatibility -> data/DB access -> performance -> logging/telemetry -> exception handling -> regression safety net`

### Reuse before creation

Search first for existing implementations, extension points, interfaces, helpers, clients, repositories, query paths, tests, configuration, loggers, and exception types serving the same responsibility. Prefer reuse, composition, narrow extension, or adapters over duplication. When reuse is rejected, record the candidate and concrete reason.

### Preserve usage patterns

Treat existing API shapes, caller behavior, configuration semantics, persisted contracts, lifecycle ordering, CLI/HTTP flows, and user-visible workflows as compatibility surfaces. Keep them unchanged unless the request explicitly requires a contract or behavior change.

### Minimize data and database calls

Inspect the existing data-access path before adding one. Prefer already-fetched state, existing caches, batching/set-based operations, joins or bulk APIs already used, and shared transaction/connection handling. Avoid N+1 queries, per-record reads, duplicate round trips, repeated hydration, and needless remote calls without weakening correctness or consistency.

### Keep performance at parity

Identify hot paths and resource-sensitive behavior. Preserve expected latency, throughput, CPU, memory, allocation, I/O, concurrency, and queue characteristics unless the request intentionally changes them. Reuse existing pooling, batching, caching, serialization, and scheduling. Measure when static reasoning cannot establish parity safely.

### Follow local logging and exception conventions

Use the repository's logger/telemetry framework, severity levels, structured fields, correlation/context, redaction, and sampling rules. Reuse existing exception types and propagation/translation patterns, preserve diagnostic context, clean up owned resources, and never swallow failures. Do not introduce a second logging/error abstraction.

### Regression is part of implementation

Verify the new requirement and affected existing behavior. Start with focused tests, then run relevant repository-native build, integration, contract, static, security, data, and performance checks. A new test passing does not prove an existing workflow was preserved.

`not_applicable: reason` is valid for a genuinely irrelevant concern; silent omission is not evidence. Higher-risk code changes block when configured quality/safety evidence is missing.

## Skill composition

- `research`: acquire uncertain external/architectural evidence before implementation.
- `prototype`: use a bounded experiment when it resolves uncertainty faster.
- `resolving-merge-conflicts`: only for active merge/rebase conflicts; preserve intent and verify.
- `interactive-documentation`: produce portable visual architecture/workflow evidence.
- `retro`: turn verified session outcomes into small durable improvements.

These are orchestration surfaces that reuse canonical repository/context/evidence/provenance stores.

## Minimal safe change

Prefer the smallest change that fully satisfies intent and preserves contracts. Reuse existing maintained implementations before adding new ones. Do not combine feature delivery with unrelated refactoring or introduce duplicate ownership.

## Runtime contracts

Keep these aligned:

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

## Evidence, rollout, and safety

Evidence must be traceable and sufficient for the claim. Verification is independent of generation; review gates the verified artifact and same evidence.

For bugs: `reproduce -> isolate -> identify owner -> minimal fix -> regression test -> verify -> review adjacent behavior`.

Deployment lineage is `research -> plan -> implement -> verify -> review -> shadow -> canary -> promote`, or rollback after a failed gate. Never bypass security, permission, scope, or regression gates. Require explicit approval for destructive, irreversible, production, financial, privacy-sensitive, or external-message actions.

## Working sequence

Normal coding:

`understand intent -> repository map -> find reusable implementation -> acquire bounded context -> declare quality evidence -> choose execution strategy -> implement -> verify -> review -> integrate -> regression -> artifact -> shadow -> canary -> promote or rollback`

Research/POC:

`define question -> bounded evidence -> research -> prototype when useful -> measure -> decide -> record unknowns -> normal implementation gates`

Visual documentation:

`audience -> repository map -> context/evidence -> typed topology -> validate -> standalone HTML -> inspect -> publish`

Review:

`acquire context -> inspect contracts and graph -> reproduce -> classify findings -> course-correct -> verify -> review`

## Output discipline

Report what changed, why, what was verified/reviewed, evidence/receipts, remaining uncertainty, reusable implementations inspected and reuse decisions, placement/dependency decisions, and relevant risks. Prefer concrete paths, symbols, tests, graph edges, snapshot digests, and lifecycle state over broad claims.
