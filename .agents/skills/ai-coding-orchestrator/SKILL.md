---
name: ai-coding-orchestrator
description: Adaptive, repository-aware software-engineering control plane for coding, debugging, research, POCs, reviews, Jira work, and safe changes. Selects only the context, workflow, tools, and optional extensions needed for the task; verifies before completion.
---

# Adaptive AI Coding Orchestrator

Use this skill as the control plane for non-trivial software-engineering work. It is provider-neutral and works with Claude Code and other Agent-Skills-compatible agents.

Default lifecycle:

`Understand -> Profile -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if needed -> Learn -> Stop`

One adaptive run is the default. Never recursively loop unless the user explicitly asks for a loop.

## Bootstrap

1. Read applicable repository/team instructions (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, local docs and skills).
2. Inspect git state, project structure, manifests, tests, and nearby implementations.
3. Profile the repository when conventions are unclear or infrastructure is affected.
4. Detect optional extensions before using them.

Never assume a language, framework, package manager, test runner, MCP server, skill, or tool exists.

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

Do not invoke Research, POC, Grill, or other skills merely because they exist. Explicit user requests take precedence over automatic routing unless unsafe.

## Knowledge and context

Treat the repository as structured evidence, not a bag of text. Prefer instructions and acceptance criteria, then AST/symbol evidence, graph relationships, exact search, semantic retrieval, targeted source reads, and finally tests/build/CI/runtime evidence.

Use Graphify and code-mem together only when their evidence is complementary. Avoid duplicate exploration and preserve provenance.

Apply the FlashAttention-inspired IO principle: keep stable instructions small, retrieve evidence in bounded tiles, rank before inclusion, avoid replaying irrelevant history, and preserve verification evidence losslessly.

## Optional extensions

Extensions are optional capabilities, never dependencies. Detect first and use only when installed, enabled, relevant, and permitted. Never install or modify them without explicit approval.

- Graphify: AST/graph/relationship/impact evidence.
- code-mem / codebase-memory-mcp: persistent code graph, semantic/structural search, call tracing and impact analysis.
- Superpowers: TDD, planning, systematic debugging and execution discipline.
- Ponytail: YAGNI and minimal-change pressure.
- Caveman: compact output/context handling.
- Other Agent Skills/MCP: use only when materially useful.

Repository/team rules, security boundaries, acceptance criteria, local architecture, and verification requirements outrank this skill and all optional extensions.

## Repository-first implementation

Before creating a file or abstraction, inspect siblings and infer maintained local patterns. Preserve naming, placement, namespace/module/package boundaries, exception handling, logging, telemetry, DI, configuration, retries, clients, dependencies, and testing conventions. Do not introduce generic `Common`, `Shared`, `Utils`, or `Helpers` locations without strong evidence.

If no compatible local pattern exists, choose a mature ecosystem convention and disclose new dependencies.

## Safety and verification

Use isolated worktrees for high-risk, experimental, long-running, or parallel mutation. Research and review are read-only. Execute generated code, tests, migrations, and scripts only through approved repository/sandbox boundaries.

A model claim is not evidence. Match verification to acceptance criteria and risk. Use focused tests plus applicable build/type/lint/static/integration/contract/security/performance/compatibility checks and review the final diff.

Every retry must add evidence or materially change the approach.

## Control-plane policies

Read detailed control-plane guidance only when needed:

- `ORCHESTRATION_SPEC.md`
- `TEN_LOOP_POLICY.md`
- `CONTEXT_POLICY.md`
- `ARCHITECTURE_POLICY.md`
- `EXECUTION_POLICY.md`
- `VERIFICATION_POLICY.md`
- `REVIEW_POLICY.md`
- `LEARNING_POLICY.md`
- `TOKEN_POLICY.md`
- `PROVIDER_CONTRACT.md`
- `QUALITY_GOVERNANCE.md`

## Progressive disclosure

Load detailed guidance only when needed:

- `references/OPERATING_MODEL.md`
- `references/EXTENSIONS.md`
- `references/CONTEXT_AND_EVALS.md`
- `.ai-harness/evals/EVAL_POLICY.md`

Do not copy these references into every prompt. Keep the skill metadata and always-needed instructions compact.

## Learning and completion

Record evidence-backed observations, route quality, verification outcomes, review findings, useful patterns, failures, and token/tool metrics when available. Promote durable knowledge only after repeated success. Learned knowledge must not silently rewrite executable harness code, security policy, provider permissions, or permanent engineering rules.

Report outcome, changed files, verification evidence, review evidence, extensions actually used, conventions reused, placement/dependency decisions, assumptions, risks, and incomplete checks.
