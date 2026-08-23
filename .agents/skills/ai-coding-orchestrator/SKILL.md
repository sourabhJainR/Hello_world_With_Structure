---
name: ai-coding-orchestrator
description: Automatically determine the engineering state, required context, capabilities, risk controls, verification strategy, model/tool budget, isolation strategy, review strategy, code placement, and stopping condition for prompts, tasks, Jira items, issues, and coding requests. Use the minimum safe workflow that achieves a verified outcome.
---

# AI Coding Orchestrator

Invoke this skill for every non-trivial software-engineering request before making changes.

## Operating contract

1. Normalize the input into task, source, Jira/issue reference, constraints, acceptance criteria, non-goals, and stopping condition.
2. Inspect repository state, applicable instructions, nearby patterns, dependency boundaries, and relevant tests.
3. Run the repository convention profiler before introducing or changing infrastructure: `python .ai-harness/project_profile.py`.
4. Reuse detected exception handling, logging, telemetry, package management, and testing conventions whenever present. Do not introduce a competing framework because it is newer or more popular.
5. If the repository is genuinely fresh, use the simplest standard-library baseline first and consult `.ai-harness/DEPENDENCIES.md` before adding any third-party library.
6. Analyze code placement before creating a new interface, class, constant, configuration, test, adapter, utility, or module. Use `python .ai-harness/placement.py <file-names>` when a new file is required.
7. If multiple locations are candidates, select the one with the strongest combination of domain cohesion, dependency direction, namespace/module consistency, sibling-code proximity, test alignment, and reuse potential. Prefer an existing cohesive location over creating a new folder or shared/common bucket.
8. Retrieve only relevant learned patterns and current evidence.
9. Classify intent, scope, risk, uncertainty, change surface, and reversibility.
10. Select the minimum useful capabilities, model tier, tool set, isolation strategy, review depth, and placement strategy.
11. Execute in a controlled loop: understand -> plan -> place -> change -> verify -> inspect diff -> review -> learn.
12. On failure, diagnose before retrying. Every retry must add new evidence or change the approach.
13. Persist a checkpoint for long-running or interrupted work so another session can resume without replaying the full transcript.
14. Stop when acceptance criteria are satisfied and evidence supports completion.
15. Never claim commands, tests, Jira data, source material, or tool usage that did not occur.

## Automatic capability routing

- `research`: unknown technology, external facts, current documentation, competing approaches, architecture decisions
- `poc`: feasibility questions, unresolved technical uncertainty, experiments that should precede production changes
- `debug`: failures, regressions, intermittent behavior, root-cause analysis
- `grill`: meaningful security, migration, performance, production, reliability, or high-risk design work
- `review`: meaningful changes, release-impacting changes, or explicit review requests
- `validate`: build, type, lint, tests, integration checks, static analysis, migration checks, and other repository-native evidence
- `learn`: extract evidence-backed lessons and task metrics after completion

Skip capabilities when repository evidence makes them unnecessary. Do not run every capability on every task.

## Existing-convention rule

The repository is the system of record for engineering conventions.

Before creating exception handling, logging, telemetry, testing, dependency injection, configuration, retry, HTTP/client infrastructure, or new file categories:

1. Search for existing implementations and sibling locations.
2. Identify the established API, folder/module/package segregation, namespace/import pattern, and usage convention.
3. Reuse it unless there is a demonstrated limitation.
4. Preserve its configuration, levels, event names, correlation IDs, test helpers, naming, and operational behavior.
5. Record a deviation when an existing pattern must be replaced.

Never create parallel logging, telemetry, error, test, common, shared, or utility abstractions merely because the harness has its own internal implementation. The harness infrastructure is not a license to impose its conventions on the application being modified.

## Code placement and segregation

New files must be placed according to the repository's current code organization.

For every new interface, class, constant, configuration file, test, adapter, client, or utility:

- inspect related types and their sibling files first
- identify the dominant folder/module/package pattern for that responsibility
- prefer the closest cohesive bounded context or feature
- keep contracts/interfaces near their owner unless the repository clearly has a dedicated contracts/ports layer
- keep constants near the owning domain unless they are genuinely cross-cutting and the repository has an established shared-constants pattern
- keep tests where the repository normally keeps tests and mirror production structure when that is the convention
- do not create `Common`, `Shared`, `Utils`, `Helpers`, or similar catch-all locations just for convenience
- do not create a new layer/folder when an existing location already serves the responsibility
- preserve language-specific namespace/package/module alignment with the chosen directory
- when two or more locations are plausible, evaluate both and choose the best architectural fit rather than the shortest path
- record the selected location and concise placement rationale in the run evidence

Placement is part of the design, not a post-processing cleanup step.

## Fresh repository rule

If the project profile shows no established convention:

- prefer standard-library or platform-native facilities
- select the most widely adopted mature framework only when a framework is required
- do not add a third-party library without an explicit dependency decision
- document the reason, version policy, security/operational impact, and alternative considered
- keep the dependency opt-in unless the task explicitly requires it
- establish a small, coherent source/test segregation before adding multiple new files

## Isolation and worktrees

Use isolated Git worktrees for:

- high or critical risk changes
- long-running tasks
- parallel mutating agents
- experiments that should not touch the primary working tree
- recovery from uncertain or failed changes

The worktree helper is:

`python .ai-harness/worktree.py create <name>`

Keep failed worktrees for inspection. Remove successful worktrees only after the branch or changes are safely preserved.

Never allow two mutating agents to edit the same files concurrently without an explicit merge strategy.

## Model routing

Use the least capable model and reasoning effort that safely solves the current phase.

- low: routing, summarization, trivial edits
- standard: normal implementation, debugging, tests
- high: architecture, hard debugging, high-risk changes
- critical: long-horizon, cross-repository, or severe production/security work

Escalate when uncertainty is unknown, risk is high/critical, verification fails repeatedly, or the task crosses significant boundaries.

## Independent review

Use read-only independent reviewers for important changes. Reviewer roles can include correctness, security, performance, and architecture.

For high-risk work prefer more than one review perspective. Reviewers must inspect the actual repository/diff rather than trusting the implementing agent's summary.

The reviewer helper is:

`python .ai-harness/review_agents.py --agent claude --run-dir <run> --task "..." --review correctness --review security`

Reviewers must not modify files. Findings are evidence for the final verification gate.

## Engineering principles

Apply `.ai-harness/principles.md` and `.ai-harness/ai-coding-best-practices.md` as decision constraints, not rituals.

Core principles include:

- DRY without premature abstraction
- YAGNI
- KISS
- dependency inversion / dependency injection where materially useful
- selective SOLID
- separation of concerns
- high cohesion / low coupling
- composition over inheritance
- least knowledge
- fail fast and explicit failure
- single source of truth
- least surprise
- make invalid states hard to represent
- compatibility by default
- behavior-focused testing
- security by default
- failure awareness
- observability
- reversibility
- least privilege
- locality of change
- evidence over assumption

For AI-specific work also apply lean prompts, explicit success criteria, bounded tool sets, minimum capable model/reasoning effort, structured checkpoints, controlled delegation, isolated execution for risky changes, independent verification, and evidence-based learning.

## Context engineering

Use the stable context prefix first:

1. repository instructions
2. project convention profile
3. code placement/segregation profile when new files are needed
4. principles and task contract
5. compact repository map
6. relevant learned memory
7. current task and acceptance criteria

Then add phase-specific evidence only.

Prefer targeted searches and summaries over full repository dumps or full previous transcripts. Preserve stable prefixes so providers that support caching can reuse them.

## Delegation

Delegate only genuinely independent work: parallel repository investigations, alternative design research, independent reviews, test planning, or security review.

Use separate worktrees for mutating parallel work. Do not parallelize edits to the same files without an explicit merge strategy.

## Verification gate

Before completion, verify as appropriate:

- acceptance criteria
- focused tests
- build/type/lint checks
- changed contracts
- error/failure paths
- security implications
- performance implications
- compatibility and migration safety
- final diff cleanliness
- file placement and segregation consistency
- independent review findings for important changes

A model's statement that the work is complete is not evidence.

## Learning contract

After a completed run, record evidence-backed observations, route quality, verification result, useful lessons, failures, reviewer findings, model/provider choice, retries, token/tool metrics when available, and placement decisions for new files. Promote durable patterns only after repeated successful observations.

Never allow one model response to rewrite harness code, security policy, provider permissions, or permanent engineering rules automatically. Self-improvement changes knowledge and routing candidates first; durable system changes require normal review and validation.

## Expected route examples

- simple edit: context -> execute -> validate -> review
- small bug: context -> debug -> execute -> validate -> review
- unknown library: research -> context -> execute -> validate -> review
- feasibility question: research -> poc -> validate -> learn
- intermittent production bug: isolated context -> debug -> execute -> validate -> independent review -> learn
- security or migration change: isolated research -> context -> execute -> validate -> security/architecture review -> grill -> learn
- parallel design options: isolated research agents -> compare -> choose -> execute in one controlled worktree -> validate
- Jira feature: retrieve available Jira context, normalize acceptance criteria, then route normally

## Token discipline

Carry conclusions, decisions, failures, open questions, checkpoints, placement decisions, and targeted evidence. Do not carry full transcripts unless required to recover missing context.

## Completion format

Return:

- outcome
- files changed
- validation evidence
- independent review evidence when used
- placement decisions and rationale for new files
- principles materially applied
- existing project conventions reused
- dependency decisions, if any
- assumptions
- remaining risks
- checkpoint or follow-up when work is intentionally incomplete
