---
name: ai-coding-orchestrator
description: Adaptive repository-aware control plane for software-engineering tasks. Routes only the work needed, retrieves bounded evidence, uses optional code-intelligence and agent skills when useful, verifies independently, and stops when the acceptance contract is proven.
---

# Adaptive AI Coding Orchestrator

Use this skill as the control plane for non-trivial software-engineering work. Keep the always-loaded contract small; load detailed guidance only when the task needs it.

Default lifecycle:

`Contract -> Profile -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if needed -> Handoff/Learn -> Stop`

One adaptive run is the default. Never recursively loop unless the user explicitly asks for a loop.

## Bootstrap

1. Read only applicable repository/team instructions and non-obvious commands/invariants.
2. Inspect git state, project structure, manifests, tests, and nearby implementations.
3. Profile the repository when conventions are unclear or infrastructure is affected.
4. Detect optional extensions before using them.

Prefer human-written repository guidance over generated inventories. Do not create or inject a large context file merely to restate information already discoverable in the repository.

## Route by need

Classify intent, scope, risk, uncertainty, reversibility, and change surface. Select the smallest safe workflow:

- `implement`: code changes
- `debug`: root-cause investigation and repair
- `research`: unknown technology or current external facts
- `poc`: unresolved feasibility or architecture uncertainty
- `review`: independent assessment
- `grill`: adversarial challenge for meaningful/high-risk work
- `validate`: repository-native proof
- `learn`: evidence-backed lessons

Do not invoke Research, POC, Grill, or other skills merely because they exist. Explicit user requests take precedence unless unsafe.

For complex work, prefer independently verifiable slices over one oversized autonomous task. Do not invent subtasks for simple work.

## Knowledge and context

Treat the repository as structured evidence, not a bag of text. Prefer acceptance criteria and local rules, then symbols/AST, graph relationships, exact search, semantic retrieval, targeted source reads, and verification evidence.

Use Graphify and code-mem together only when their evidence is complementary. Deduplicate overlapping evidence and preserve provenance.

Apply the FlashAttention-inspired IO principle: keep stable instructions small, retrieve evidence in bounded tiles, rank before inclusion, reuse stable evidence, and avoid replaying irrelevant history.

Optimize for verified outcome per total model call/token cost, not minimum input tokens alone. A shorter prompt that causes retries is not an optimization.

## Context boundaries

When a task crosses a context/session boundary, create a compact durable handoff containing only:

`TASK, CONTRACT, DONE, OPEN, EVIDENCE, RISKS, NEXT`

Rehydrate missing facts from the repository. Do not copy the full transcript or source into the next session.

Load detailed guidance only when needed:

- `references/OPERATING_MODEL.md`
- `references/EXTENSIONS.md`
- `references/CONTEXT_AND_EVALS.md`
- `.ai-harness/evals/EVAL_POLICY.md`
- `docs/CONTEXT_EFFICIENCY.md`
- `docs/SESSION_HANDOFF_AND_ENTROPY.md`
- `docs/VERIFICATION_INDEPENDENCE.md`

## Optional extensions

Extensions are optional capabilities, never dependencies. Detect first and use only when installed, enabled, healthy enough, relevant, and permitted. Never install or modify them without explicit approval.

- Graphify: AST/graph/relationship/impact evidence.
- code-mem / codebase-memory-mcp: persistent code graph, semantic/structural search, call tracing and impact analysis.
- Superpowers: TDD, planning, systematic debugging and execution discipline.
- Ponytail: YAGNI and minimal-change pressure.
- Caveman: compact output/context handling.
- Other Agent Skills/MCP: use only when materially useful.

Repository/team rules, security boundaries, acceptance criteria, local architecture, and verification requirements outrank this skill and all optional extensions.

## Repository-first implementation

Before creating a file or abstraction, inspect siblings and infer maintained local patterns. Preserve naming, placement, namespace/module/package boundaries, exception handling, logging, telemetry, DI, configuration, retries, clients, dependencies, and testing conventions.

If no compatible local pattern exists, choose a mature ecosystem convention and disclose new dependencies.

## Verification

A model claim is not evidence. Match verification to acceptance criteria and risk. Prefer focused proof, then add broader checks only when they increase confidence.

For meaningful/high-risk changes, use a fresh reviewer context when practical. The reviewer receives the contract, final diff, relevant evidence, and verification expectations, not the full implementation transcript. Check for false-positive tests, missing negative/boundary paths, compatibility failures, and downstream impact.

After substantial work, perform a focused entropy check for stale docs/comments/tests, dead code, duplicate implementations, temporary artifacts, and unresolved merge remnants. Do not turn it into unrelated cleanup.

Every retry must add evidence or materially change the approach. Stop when the acceptance contract is proven.

## Safety and execution

Use isolated worktrees for high-risk, experimental, long-running, or parallel mutation. Research and review are read-only. Execute generated code, tests, migrations, and scripts only through approved repository/sandbox boundaries.

## Learning

Record evidence-backed observations, route quality, verification outcomes, review findings, useful patterns, failures, and token/tool metrics when available. Promote durable knowledge only after repeated success and evaluation. Learned knowledge must not silently rewrite executable harness code, security policy, provider permissions, or permanent engineering rules.

Report outcome, changed files, verification evidence, review evidence, extensions actually used, conventions reused, placement/dependency decisions, assumptions, risks, incomplete checks, and relevant efficiency metrics.
