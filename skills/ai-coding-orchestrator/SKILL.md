---
name: ai-coding-orchestrator
description: Use for non-trivial software-engineering work. Automatically profile the repository, detect available code-intelligence and process skills, choose the smallest safe workflow, retrieve precise context, implement using local conventions, verify, review, repair, and stop when evidence is sufficient. Works with Claude Code and other Agent-Skills-compatible coding agents. Optional integrations are used only when installed and enabled.
---

# AI Coding Orchestrator

This skill is the provider-neutral control plane for software creation. It is one adaptive run by default. It never recursively loops unless the user explicitly asks for a loop.

## 1. Bootstrap and inspect

Before non-trivial work:

1. Read applicable `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, repository docs, and local skill instructions.
2. Inspect git state, project structure, package/build manifests, tests, and nearby implementations.
3. Run the repository profiler when conventions are unclear or infrastructure changes are involved.
4. Detect optional extensions with `.ai-harness/extension_registry.py` when available.

Never assume a tool, MCP server, skill, framework, language, package manager, or test runner exists.

## 2. Extension-aware orchestration

Use installed extensions as capabilities, not as dependencies. Never install or modify an extension without explicit user approval.

Preferred capability mapping:

- `graphify`: deterministic AST/knowledge graph, graph traversal, impact and relationship evidence.
- `code-mem` / `codebase-memory-mcp`: persistent code graph, structural search, semantic code search, impact and call tracing.
- `superpowers`: process discipline such as brainstorming, TDD, systematic debugging, planning, execution, and skill-development patterns. Invoke the specific applicable skill rather than copying its whole workflow.
- `ponytail`: YAGNI/minimal-change discipline. Use as a design constraint when available; never let terseness remove required validation, security, error handling, or requested behavior.
- `caveman`: output/context compression. Use for compact communication and subagent output when available; never compress source code, commands, errors, acceptance criteria, or verification evidence lossily.
- Other compatible skills/MCP servers: discover, classify, and use only when they materially improve the current task.

Extension precedence:

1. Repository/team instructions.
2. Security and permission boundaries.
3. Task acceptance criteria.
4. Existing repository architecture and conventions.
5. Verification requirements.
6. This orchestrator.
7. Optional extension guidance.
8. Model preference.

If two extensions conflict, keep the higher-precedence rule and use the narrowest useful capability from each.

## 3. Knowledge fabric

Treat the repository as structured evidence, not a bag of text. Prefer:

1. Repository instructions and task constraints.
2. Fresh AST/symbol/index evidence.
3. Graph traversal for callers, callees, ownership, dependencies, flows, and blast radius.
4. Exact search for identifiers, APIs, errors, routes, configuration, and logs.
5. Semantic retrieval when an installed provider supports it.
6. Targeted source reads.
7. Tests, builds, CI, runtime output, and git diff as verification evidence.

Use Graphify and code-mem together when both exist only when their evidence is complementary. Do not duplicate the same query through both providers without a reason. Prefer the fresher or more authoritative result and record provenance.

## 4. Context engineering

Use the FlashAttention-inspired IO principle: keep stable instructions small and reusable; retrieve context in tiles; rank before inclusion; avoid replaying irrelevant history; preserve verification evidence.

Do not send an entire repository or transcript to the model merely because it is available.

Prefer symbol signatures, graph paths, relevant functions, focused diffs, current failures, and compact decisions over whole files when sufficient.

## 5. Task routing

Classify intent, risk, uncertainty, scope, reversibility, and change surface. Select only the capabilities needed:

- research: unknown technology or current external facts
- poc: unresolved feasibility or architecture uncertainty
- debug: failure/root-cause work
- implement: code changes
- validate: repository-native evidence
- grill: adversarial high-risk challenge
- review: independent review
- learn: evidence-backed post-run lessons

Use the smallest safe model/reasoning/tool budget. Escalate on high risk, unknown uncertainty, failed verification, or significant architectural boundaries.

## 6. Repository-first implementation

Before creating a file or abstraction:

- inspect related siblings;
- infer naming and coding style from maintained local code;
- compare candidate locations;
- choose the most mature compatible local pattern;
- preserve namespace/module/package alignment;
- reuse existing exception, logging, telemetry, DI, retry, HTTP/client, configuration, dependency, and testing patterns;
- do not create `Common`, `Shared`, `Utils`, `Helpers`, or catch-all folders for convenience;
- document material placement or architectural deviations.

If no local convention exists, choose the current mature ecosystem convention appropriate to the repository and document any new dependency.

## 7. Safe execution

Use isolated worktrees for high/critical-risk, experimental, long-running, or parallel mutating work. Research and review are read-only.

Generated code, tests, migrations, or scripts must run only through the repository's approved sandbox/permission boundary. Never bypass user permissions or execute against production systems.

## 8. Verification-first completion

A model's claim of success is not evidence. Require task-specific proof:

- acceptance criteria;
- focused tests;
- build/type/lint/static checks as applicable;
- integration/contract checks;
- failure-path checks;
- security/performance/compatibility checks when relevant;
- clean final diff;
- independent review for meaningful/high-risk changes.

Every retry must add evidence or materially change the approach.

## 9. Learning

Record evidence-backed observations, route quality, verification outcomes, reviewer findings, useful patterns, failures, and token/tool metrics when available. Promote durable knowledge only after repeated success. Learned knowledge may influence routing and retrieval but may not silently rewrite executable harness code, security policy, provider permissions, or permanent engineering rules.

## 10. Completion

Report outcome, files changed, verification evidence, review evidence, extensions actually used, repository conventions reused, placement decisions, dependency decisions, assumptions, risks, and incomplete checkpoints.
