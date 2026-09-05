---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for precise task execution, evidence-based RCA, minimal safe changes, verification, collaboration and bounded learning across Claude Code, Codex, Gemini and ChatGPT/Codex surfaces.
---

# Adaptive AI Coding Orchestrator

## Provider-neutral contract

AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. The active AI provider supplies inference and native tools; it must not redefine AER semantics.

Provider projection:
- Claude Code: `CLAUDE.md` + this skill + hooks/MCP when available.
- Codex: `AGENTS.md` + supported skills/MCP/plugins.
- Gemini: `GEMINI.md` + hierarchical/JIT context + extensions/MCP/A2A when available.
- ChatGPT: use the ChatGPT project/app, Codex-in-ChatGPT, or an approved MCP/API execution surface. Never assume ordinary ChatGPT chat is a local shell.

Preserve the same `intent_digest`, boundaries, acceptance criteria, protected behavior, capability plan and verification evidence across providers. Unsupported capabilities are explicitly recorded as unavailable; never inferred.

## Progressive discovery

Keep always-active context small. Do not preload the full AER methodology, every policy, framework, history, capability, repository dump or transcript.

Runtime context follows:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.

The Context Broker decides what becomes active next. Retrieve only what the current phase, uncertainty, dependency, risk or verification gate justifies. Prefer targeted source reads and structural evidence over large prompt dumps. Release raw context after the decision and retain compact references, decisions, digests and proof-bearing evidence.

## Lifecycle

`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair if justified -> Learn -> Self-modify -> Regression -> Safety -> Shadow -> Canary -> Promote -> Monitor -> Rollback -> Stop`.

Normal mode is one bounded adaptive run. Never create an unrestricted autonomous loop. Repetition requires explicit attempt/time/token/risk budgets, measurable acceptance criteria and an evaluation gate.

## Task contract

Create or load:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.
Carry the intent digest through phases, graph nodes, retries, resumes and handoffs.

## Repository-first engineering

Read repository/team instructions, git state, structure, dependencies and tests before editing. Reuse local architecture, naming, placement, error handling, logging, telemetry, DI, configuration and test patterns. Make the minimal safe change. Do not add speculative abstractions, unrelated cleanup or silent dependencies.

Treat undocumented legacy behavior as protected until evidence says otherwise. Trace callers, branches, feature/config gates, persistence, integrations, failure paths and data shapes. Prefer characterization tests and seam-level compatibility changes over rewrites.

## Agent, loop, graph and orchestration

`Agent -> bounded Loop -> Graph -> Orchestration`.

- Agent: one focused capability such as exploration, implementation, verification, review or RCA.
- Loop: `Plan -> Act -> Observe -> Evaluate`, with bounded repair only when new evidence or a changed strategy justifies it.
- Graph: explicit nodes, dependencies, inputs/outputs, risk and mutation boundaries. Reject cycles unless represented as bounded retry/repair.
- Orchestration: owns contracts, scheduling, budgets, evidence, policy, verification, recovery, learning and lifecycle.

Execute only nodes whose dependencies and policy gates pass. Parallelize only independent read-only work. Never parallelize conflicting writes. Failed evaluators block dependent nodes unless an explicit recovery path permits progress.

## Evidence and verification

Treat the agent plus harness as the system under evaluation. Retain:
`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.

Verification outranks model confidence. Use layered checks:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

For self-modifying candidates, static validation must never execute generated code. Candidate behavior runs only inside the isolated regression/safety evaluation boundary. A model suggestion is not evidence of improvement.

When tests are weak, add characterization, invariant, metamorphic or property-based checks where appropriate. Never claim commands, tests or absence of regressions that were not observed.

## Capability planning and collaboration

Before provider execution, record a deterministic `capability-plan.json`. Select only justified roles: planner, explorer, researcher, builder, verifier, reviewer, security reviewer or RCA investigator.

For provider tools/MCP, negotiate minimum permissions per phase. Read-only investigation precedes mutation when practical. Preserve compact tool observations with provider, phase, permission mode, input/output digests and status.

Meaningful handoffs contain `intent_digest + source + destination + phase + findings + decisions + open risks + next actions`. Validate intent and scope before consuming a handoff.

## RCA

For RCA, diagnosis or investigation without an explicit fix request: do not edit, commit, push or patch. Trace source/tests/history/logs/persistence/integrations, compare data shapes, classify `Fact | Inference | Unknown | Recommendation`, attach evidence and report root cause as `proven | probable | unproven`.

## Regression replay

A regression is durable learning evidence:
1. Capture baseline outcome and evidence.
2. Add/reference a deterministic reusable regression case.
3. Replay against candidate behavior.
4. Compare acceptance, safety and compatibility outcomes.
5. Reject candidates that introduce known regressions or weaken protected behavior.
6. Strengthen weak tests before treating a candidate as verified.
7. Only then run safety, shadow and canary evaluation.

Nondeterministic tests must expose uncertainty rather than being treated as clean passes.

## Learning and self-improvement

Use:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Record evidence-backed outcomes, reviewer findings, retries, regressions and DO/DON'T lessons. Promote patterns only after repeated evidence and evaluation. Candidate executable orchestration changes remain candidates until regression and safety gates pass.

Candidate selection must favor measurable improvement over a known baseline while preserving protected behavior, reducing regressions and maintaining verification quality. Maintain representative regression families to reduce overfitting.

Learned behavior may improve retrieval, routing, node selection, retry strategy, graph topology and orchestration decisions. It must never silently expand credentials, permissions or protected security boundaries.

Promoted behavior is versioned, content-addressed and reversible. Retain parent/source digests, regression and safety evidence, promotion decision and rollback lineage.

## Context economics

Treat the repository as structured evidence. Prefer rules/acceptance, AST/symbol/dependency structure, impact paths, exact search, configured semantic retrieval, targeted reads and verification output. Keep stable context small, rank evidence, compact history by information value, preserve proof-bearing state, reuse summaries and avoid transcript replay. Optimize verified outcome per token, call, retry and latency.

## Engineering State Ledger

For non-trivial work maintain:
`INTENT | CONTRACT | REPO_FACTS | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.
For self-modification also retain:
`CANDIDATE_ID | PARENT_DIGEST | SOURCE_DIGEST | REGRESSION | SAFETY | PROMOTION | ACTIVE_VERSION | ROLLBACK_TARGET`.

## Recovery, safety and installation

Failures are classified before recovery. Use targeted repair; do not restart the entire graph unless its contract or required evidence is invalid. Every promoted behavioral change must remain reversible. Security, permission and protected-behavior gates cannot be bypassed by learned strategies or retries.

When installed globally, AER runtime, policies, journals, learning state and caches stay outside the workspace. Do not manually mix versions or modify repository configuration during installation. Use the installed CLI for upgrades.

Extensions are optional capabilities, never dependencies. Detect first; use only when available, healthy, relevant and permitted.

Precedence: `Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion

Report: `Outcome | Changed files | Evidence | Verification | Regression checks | Review | Capability plan | Graph/loop summary | Learning signal | Self-modification candidate/promotion | Assumptions | Risks | Incomplete checks | Efficiency`.

Policies: `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md`, `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`, `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `PROVIDER_MATRIX.json`, `QUALITY_GOVERNANCE.md`.
