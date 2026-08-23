---
name: ai-coding-orchestrator
description: Use for non-trivial software-engineering work. Automatically profile the repository, detect available code-intelligence and process skills, choose the smallest safe workflow, retrieve precise context, implement using local conventions, verify, review, repair, and stop when evidence is sufficient. Works with Claude Code and other Agent-Skills-compatible coding agents. Optional integrations are used only when installed and enabled.
---

# AI Coding Orchestrator

This skill is the provider-neutral control plane for software creation. It is one adaptive run by default. It never recursively loops unless the user explicitly asks for a loop.

## Bootstrap

1. Read applicable `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, repository docs, and local skills.
2. Inspect git state, project structure, manifests, tests, and nearby implementations.
3. Run the repository profiler when conventions are unclear or infrastructure changes are involved.
4. Detect optional extensions with `python .ai-harness/extension_registry.py` when available.

Never assume a tool, MCP server, skill, framework, language, package manager, or test runner exists.

## Optional extension orchestration

Use installed extensions as capabilities, not dependencies. Never install or modify an extension without explicit user approval.

- `graphify`: AST/knowledge graph, relationship queries, impact and path evidence.
- `code-mem` / `codebase-memory-mcp`: persistent code graph, structural/semantic search, impact and call tracing.
- `superpowers`: applicable process skills such as brainstorming, TDD, systematic debugging, planning, execution, and skill development.
- `ponytail`: YAGNI/minimal-change discipline; never trade away correctness, security, error handling, accessibility, or acceptance criteria.
- `caveman`: compact communication and subagent output; never lossily compress source, commands, errors, acceptance criteria, or verification evidence.
- Other Agent Skills/MCP servers: discover and use only when they materially improve the task.

Extension precedence:

1. Repository/team instructions.
2. Security and permission boundaries.
3. Acceptance criteria.
4. Existing repository architecture/conventions.
5. Verification requirements.
6. This orchestrator.
7. Optional extension guidance.
8. Model preference.

When extensions conflict, retain the higher-precedence rule and use the narrowest useful capability from each.

## Knowledge fabric

Treat the repository as structured evidence:

1. instructions and task constraints;
2. AST/symbol/index evidence;
3. graph traversal for callers, callees, ownership, dependencies, flows, and blast radius;
4. exact search for identifiers, APIs, errors, routes, configuration and logs;
5. semantic retrieval when available;
6. targeted source reads;
7. tests, build/CI output and final diff as verification evidence.

When Graphify and code-mem are both available, use them only for complementary evidence. Prefer the fresher or more authoritative result and preserve provenance.

## Context engineering

Apply the FlashAttention-inspired IO principle: keep stable instructions small and reusable, retrieve evidence in tiles, rank before inclusion, avoid replaying irrelevant history, and preserve verification evidence.

Prefer symbols, signatures, graph paths, focused diffs, current failures and compact decisions over whole repositories or transcripts.

## Routing

Classify intent, risk, uncertainty, scope, reversibility, and change surface. Select only what is needed:

- research: unknown technology/current facts
- poc: unresolved feasibility
- debug: root-cause work
- implement: code changes
- validate: repository-native evidence
- grill: adversarial challenge
- review: independent review
- learn: evidence-backed lessons

Use the smallest safe model/reasoning/tool budget. Escalate on high risk, unknown uncertainty, failed verification, or major boundaries.

## Repository-first implementation

Before creating a file or abstraction:

- inspect related siblings;
- infer naming and coding style from maintained local code;
- compare candidate locations;
- choose the most mature compatible local pattern;
- preserve namespace/module/package alignment;
- reuse existing exception, logging, telemetry, DI, retry, client, configuration, dependency and testing patterns;
- never create `Common`, `Shared`, `Utils`, `Helpers`, or catch-all folders for convenience;
- document material placement or architectural deviations.

If no local convention exists, use a current mature ecosystem convention appropriate to the repository and document any new dependency.

## Safe execution and verification

Use isolated worktrees for high/critical-risk, experimental, long-running, or parallel mutating work. Research and review are read-only. Use the repository's approved sandbox/permission boundary for generated code, tests, migrations, and scripts.

A model's claim of success is not evidence. Require acceptance criteria, focused tests, build/type/lint/static checks, integration/contract checks, failure-path checks, security/performance/compatibility checks when relevant, clean diff, and independent review for meaningful/high-risk changes.

Every retry must add evidence or materially change the approach.

## Learning and completion

Record evidence-backed observations, route quality, verification outcomes, review findings, useful patterns, failures, and token/tool metrics when available. Promote durable knowledge only after repeated success. Learned knowledge must not silently rewrite executable harness code, security policy, provider permissions, or permanent engineering rules.

Report outcome, files changed, validation evidence, review evidence, extensions used, conventions reused, placement decisions, dependency decisions, assumptions, risks, and incomplete checkpoints.
