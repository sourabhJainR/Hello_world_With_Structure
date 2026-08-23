# Repository AI Agent Instructions

This repository uses an adaptive, provider-neutral AI coding orchestrator. These instructions apply to Claude Code, Codex, Gemini, local agents, and other compatible AI coding tools.

Canonical control plane: `.agents/skills/ai-coding-orchestrator/SKILL.md`.
Core orchestration contract: `.ai-harness/ORCHESTRATION_SPEC.md`.
Ten-pass review loop: `.ai-harness/TEN_LOOP_POLICY.md`.

## Default workflow

For every non-trivial software-engineering task:

1. Understand the request, source, Jira or issue context, constraints, acceptance criteria, non-goals, and stopping condition.
2. Inspect repository structure, instructions, dependencies, tests, nearby implementations, and current git state before changing code.
3. Run the repository convention profiler when introducing or changing infrastructure or when the repository pattern is unclear.
4. Infer the minimum safe capabilities needed. Research, POC, Debug, Grill, Review, Validation, and Learning are selected automatically when useful.
5. Select the smallest safe model, tool, context, and reasoning budget and escalate only when risk, uncertainty, scope, or failed verification warrants it.
6. Follow the ten-pass loop: intake, profile, context/placement, design/risk, implementation, verification, adversarial review, repair/regression, optimization/cleanup, final acceptance/learning. Early exit is allowed only when policy permits it.
7. Implement using the repository's established architecture, naming, coding style, segregation, exception handling, logging, telemetry, dependency, and testing patterns.
8. Verify using repository-native evidence, inspect the final diff, and use independent review for meaningful or high-risk changes.
9. Learn only from evidence-backed outcomes. Never silently rewrite harness code, security policy, provider permissions, or permanent engineering rules.

## Existing repository conventions are authoritative

The repository is the system of record for engineering conventions.

Before creating or changing exception handling, logging, telemetry, testing frameworks, dependency injection, configuration, retries, HTTP/external clients, serialization, validation, error/result types, build, or packaging, search for existing implementations and reuse them.

Do not introduce a competing framework because it is newer, fashionable, or familiar to the agent.

## Naming and coding-style precedence

When naming files, types, functions, variables, tests, modules, namespaces, packages, or configuration:

1. Follow explicit repository or team instructions.
2. Follow the dominant local convention for the same responsibility.
3. When multiple local patterns exist, choose the most mature pattern that is compatible, scalable, maintainable, testable, and already used for comparable code.
4. Only when no meaningful local convention exists, use a current, mature, widely adopted ecosystem convention appropriate to the language and repository type.
5. Record a deviation when a deliberate exception is necessary.

Do not mix naming styles merely for consistency with an external framework. Local consistency and compatibility take precedence.

## File placement and segregation

New interfaces, classes, constants, services, handlers, models, adapters, clients, configuration, and tests must be placed according to the current repository segregation.

Before creating a new file:

1. Find related sibling files.
2. Identify candidate directories or modules.
3. Compare candidates using responsibility, domain cohesion, dependency direction, namespace/module/package alignment, neighboring naming, test proximity, reuse, scalability, and compatibility.
4. Prefer the strongest existing location.
5. Prefer an existing cohesive directory over creating a new layer or folder.
6. Keep contracts close to their owning abstraction unless the repository has a dedicated contracts layer.
7. Keep constants close to the bounded context that owns them unless they are genuinely cross-cutting and the repository has a shared convention.
8. Keep tests in the established test structure and mirror production organization when that is the local pattern.
9. Do not create generic Common, Shared, Utils, Helpers, Misc, or similar locations merely for convenience.
10. Record the placement decision and rationale in run evidence.

Use the placement analyzer when candidate locations are ambiguous: `python .ai-harness/placement.py <new-file-names>`.

## Language neutrality

Apply principles in terms of behavior, contracts, dependencies, state, data, risk, and architecture. Adapt the implementation to the language and ecosystem already present.

Do not impose language-specific patterns, interfaces, constructors, module layouts, asynchronous models, dependency-injection frameworks, or testing libraries when the repository already has a better equivalent.

## Engineering principles

Apply these proportionally, not as rituals:

- DRY without premature abstraction
- YAGNI
- KISS
- Dependency Inversion / Dependency Injection where materially useful
- SOLID selectively
- Separation of Concerns
- High Cohesion / Low Coupling
- Composition over Inheritance
- Least Knowledge
- Fail Fast and Explicit Failure
- Single Source of Truth
- Least Surprise
- Make Invalid States Hard to Represent
- Compatibility by Default
- Behavior-Focused Testing
- Security by Default
- Failure Awareness
- Observability
- Reversibility
- Least Privilege
- Locality of Change
- Evidence Over Assumption

## Fresh repository and third-party dependencies

If the project has no established implementation pattern:

- prefer standard-library or platform-native capabilities first;
- use a mature, widely adopted framework only when a framework is warranted;
- do not add third-party dependencies silently;
- check `.ai-harness/DEPENDENCIES.md` before introducing one;
- document purpose, scope, version policy, operational/security impact, and alternatives considered;
- keep optional capabilities opt-in unless the task requires them.

## Isolation and safety

Use isolated Git worktrees for high-risk, critical, long-running, experimental, or parallel mutating work.

Never allow multiple mutating agents to edit the same files concurrently without an explicit merge strategy.

Research and Grill are read-only by contract. POCs are experimental. Production modifications happen only in controlled execution phases.

## Verification

A model's statement that work is complete is not evidence.

Before completion, use appropriate repository-native verification such as acceptance criteria, focused tests, integration tests, build/type/lint checks, static analysis, contract checks, error/failure paths, security checks, performance checks, migration/compatibility checks, final git diff and whitespace validation, and independent review for meaningful or high-risk changes.

Every retry must add new evidence or materially change the approach.

## Context and token discipline

Use stable repository instructions and compact context first. Prefer targeted reads, repository maps, relevant memory, current command output, and compact phase summaries over full repository dumps or full transcripts.

Carry conclusions, decisions, failures, open questions, checkpoints, and evidence. Do not carry irrelevant history.

## Self-improvement

Record evidence-backed observations, useful lessons, route quality, verification outcomes, review findings, retries, and available token/tool metrics.

Promote durable patterns only after repeated successful observations. Learned knowledge may improve routing and future context selection, but must not silently modify executable harness code, security policy, provider permissions, or permanent engineering rules.

## Completion report

Report outcome, files changed, validation evidence, independent review evidence when used, existing repository conventions reused, placement decisions, dependency decisions, principles materially applied, assumptions, remaining risks, and checkpoint or next action when intentionally incomplete.
