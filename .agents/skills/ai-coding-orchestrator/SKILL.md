---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane that discovers only the context and capabilities required for the current task, then executes bounded, evidence-driven work.
---

# Adaptive AI Coding Orchestrator

## Core rule: progressive disclosure

Keep the always-active context intentionally small. Do **not** preload the full AER methodology, every policy, every framework, history, or every capability into the model context.

Start with:
`GOAL -> BOUNDARIES -> REPO PROFILE -> REQUIRED EVIDENCE -> ROUTE -> EXECUTE -> VERIFY`.

At each step, discover only what is required by the current evidence and task state. Load a policy, framework, skill, history slice, tool capability or repository file **just before it becomes relevant**. After use, retain only its decisions, constraints and proof-bearing outputs in the Engineering State Ledger; do not carry the full source text forward.

Progressive discovery order:
1. Task intent and acceptance.
2. Repository/team rules and protected behavior.
3. Exact files, symbols, tests, dependencies and failure evidence needed for the current decision.
4. One problem-solving framework when justified.
5. One capability/agent role when justified.
6. Additional policies, history, tools or context only when evidence creates the need.
7. Verification evidence and only the minimum state required for the next phase.

Never retrieve context merely because it exists. Context must answer a current question, satisfy a gate, reduce material uncertainty, or provide required evidence.

## Task contract

Create/load the minimum contract:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED_BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.
Carry the compact `intent_digest`, decisions and evidence through phases; do not carry raw conversation or large documents unless re-retrieval is necessary.

## Repository-first

Before editing, discover repository instructions, git state, structure, relevant dependencies and tests. Use targeted search and reads rather than broad file loading. Reuse local architecture, naming, error handling, logging, configuration and test patterns. Make the minimal safe change.

Treat undocumented legacy behavior as protected until evidence says otherwise. Trace only the callers, persistence, integrations, failure paths and data shapes relevant to the change. Prefer characterization and seam-level compatibility tests over rewrites.

## Adaptive problem solving

Select the **smallest useful** framework from `.ai-harness/PROBLEM_SOLVING_FRAMEWORKS.md`; load that framework only when the task reaches the decision it supports:
- OODA: changing incidents/evidence.
- DMAIC: measurable optimization/process improvement.
- 5 Whys/RCA: defects and recurring failures.
- Pre-Mortem: consequential changes/releases/migrations/self-modification.
- First Principles: POCs, architecture, assumption-heavy work.
- Six Thinking Hats: multi-perspective review/decisions.
- Decision Tree: uncertainty, tradeoffs, reversibility.

Do not run all seven mechanically. Record compactly:
`FRAMEWORK | PURPOSE | KEY_FINDINGS | DECISION | EVIDENCE | NEXT`.
RCA additionally records `SYMPTOM | 5_WHYS | ROOT_CAUSE_CONFIDENCE | CONTAINMENT | CORRECTIVE_ACTION | PREVENT_RECURRENCE`.

## Capability discovery

Do not activate every agent, tool, extension or workflow. First determine the missing capability. Then discover/select only the required role: `planner | explorer | researcher | builder | verifier | reviewer | security | RCA`.

Use extensions only when detected, healthy, relevant and permitted. Extensions are optional capabilities, never dependencies.

## Bounded execution

Lifecycle is demand-driven:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Plan -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn`.

Use `Agent -> bounded Loop -> Graph -> Orchestration` only as complexity requires. A loop is `Plan -> Act -> Observe -> Evaluate`; every retry has explicit attempt/time/token/risk limits. Graphs have explicit dependencies, inputs/outputs, risk and mutation boundaries. Reject unbounded cycles. Parallelize only independent read-only work.

Failed evaluators block dependents unless an explicit recovery path permits progress.

## Verification

Verification outranks model confidence. Discover and run only the tests/checks relevant to changed behavior, then expand when evidence requires it:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Regression replay compares baseline/candidate behavior against acceptance, safety and compatibility. Nondeterminism is exposed, not silently treated as a pass.

## Learning and self-modification

Learning is also progressive: retrieve the smallest evidence set needed to form a candidate. Use:
`Observe -> Outcome -> Candidate -> Regression -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Self-modifying candidates never become active from model output alone. Static validation must not execute generated code. Promoted behavior is versioned, content-addressed, evidence-backed and reversible, retaining parent/source digests and rollback lineage.

## State and context economics

Maintain a compact Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

For self-modification add only when applicable:
`CANDIDATE_ID | PARENT_DIGEST | SOURCE_DIGEST | REGRESSION | SAFETY | PROMOTION | ACTIVE_VERSION | ROLLBACK_TARGET`.

Prefer references, summaries and hashes over copied source. Re-retrieve source when needed instead of retaining large context. Optimize verified outcome per token/call/retry/latency.

## Policy discovery map

Policies are **on-demand references**, not default context. Resolve and read only the policy needed for the current gate:
- orchestration/routing -> `ORCHESTRATION_SPEC.md`
- context/token budget -> `CONTEXT_POLICY.md`, `TOKEN_POLICY.md`
- execution/loops -> `EXECUTION_POLICY.md`, `TEN_LOOP_POLICY.md`
- verification/review -> `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`
- learning/self-modification -> `LEARNING_POLICY.md`
- architecture/provider -> `ARCHITECTURE_POLICY.md`, `PROVIDER_CONTRACT.md`
- quality/governance -> `QUALITY_GOVERNANCE.md`
- problem solving -> `PROBLEM_SOLVING_FRAMEWORKS.md`

Do not read all policies at startup. If a policy is not relevant to the current action, leave it undiscovered.

## Recovery and safety

Classify the failure before repair. Use targeted recovery; do not restart the entire graph by default. Security, permission, acceptance and protected-behavior gates cannot be bypassed.

## Installation and upgrades

Global AER state stays outside workspaces. Use the installed CLI for upgrades. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` defines side-by-side, state-preserving, verified, atomic, rollback-capable upgrades; downgrades require explicit rollback. Same-version/different-hash artifacts are distinct immutable builds. New behavior activates only after validation/gates.

## Completion

Report compactly:
`Outcome | Changed files | Evidence | Verification | Regression | Review | Capabilities | Framework | Assumptions | Risks | Incomplete checks | Efficiency`.

### Non-negotiable precedence

`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.
