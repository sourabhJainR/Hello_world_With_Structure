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
7. If multiple locations are candidates, select the one with the strongest combination of domain cohesion, dependency direction, namespace/module consistency, sibling-code proximity, test alignment, maintainability, compatibility, and reuse potential. Prefer an existing cohesive location over creating a new folder or shared/common bucket.
8. Retrieve only relevant learned patterns and current evidence.
9. Classify intent, scope, risk, uncertainty, change surface, and reversibility.
10. Select the minimum useful capabilities, model tier, tool set, isolation strategy, review depth, and placement strategy.
11. Execute under the ten-pass policy in `.ai-harness/TEN_LOOP_POLICY.md`. Early exit is allowed only when the acceptance gates are met and skipped passes are demonstrably unnecessary for the task risk profile.
12. On failure, diagnose before retrying. Every retry must add new evidence or change the approach.
13. Persist a checkpoint for long-running or interrupted work so another session can resume without replaying the full transcript.
14. Stop when acceptance criteria are satisfied and evidence supports completion.
15. Never claim commands, tests, Jira data, source material, or tool usage that did not occur.

## Ten-pass loop

1. Intake and intent: define the required outcome, constraints, acceptance criteria, and stopping condition.
2. Repository profile: establish language, naming, segregation, dependencies, tests, logging, telemetry, exception, and architectural conventions.
3. Context and placement: gather only relevant evidence and select the best location and naming style for new code.
4. Design and risk: choose the smallest safe approach, dependencies, contracts, failure modes, and rollback path.
5. Implementation: make the smallest compatible change using existing patterns.
6. Verification: produce direct acceptance evidence plus repository-native validation.
7. Adversarial review: independently challenge correctness, security, reliability, performance, architecture, compatibility, and test coverage as relevant.
8. Repair and regression: diagnose material findings, repair them, and rerun focused then broad validation.
9. Optimization and cleanup: remove unnecessary code, context, dependencies, tool calls, and complexity without weakening guarantees.
10. Final acceptance and learning: confirm all gates, record evidence and lessons, and leave a resumable checkpoint if incomplete.

Passes 6, 7, 8, and 10 are mandatory for high/critical risk work.

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
2. Identify the established API, folder/module/package segregation, namespace/import pattern, naming style, and usage convention.
3. If multiple local patterns exist, prefer the maintained, more scalable, more testable, more compatible pattern rather than the newest-looking pattern.
4. Reuse it unless there is a demonstrated limitation.
5. Record a deviation when an existing pattern must be replaced.

Never create parallel logging, telemetry, error, test, common, shared, or utility abstractions merely because the harness has its own internal implementation. The harness infrastructure is not a license to impose its conventions on the application being modified.

## Code placement and naming

For every new interface, class, constant, configuration file, test, adapter, client, or utility:

- inspect related types and sibling files first;
- identify the dominant folder/module/package pattern for that responsibility;
- infer naming from maintained siblings, including file names, type names, constants, test names, and namespace/package/module structure;
- prefer the existing naming convention even when another convention is more fashionable;
- if multiple local styles exist, choose the most advanced maintained pattern that remains compatible with the surrounding code;
- prefer the closest cohesive bounded context or feature;
- keep contracts/interfaces near their owner unless the repository clearly has a dedicated contracts/ports layer;
- keep constants near the owning domain unless they are genuinely cross-cutting and the repository has an established shared-constants pattern;
- keep tests where the repository normally keeps tests and mirror production structure when that is the convention;
- do not create `Common`, `Shared`, `Utils`, `Helpers`, or catch-all folders just for convenience;
- preserve language-specific namespace/package/module alignment with the chosen directory;
- when two or more locations are plausible, evaluate the candidates and choose the strongest architectural fit;
- record the selected path, naming pattern, candidates considered, and rejection reason for material alternatives in run evidence.

If no local convention exists for the new construct, use the current broadly adopted ecosystem convention that is mature, compatible, well-supported, and appropriate to the repository rather than inventing a custom style.

## Fresh repository rule

If the project profile shows no established convention:

- prefer standard-library or platform-native facilities;
- select the most widely adopted mature framework only when a framework is required;
- do not add a third-party library without an explicit dependency decision;
- document the reason, version policy, security/operational impact, and alternative considered;
- keep the dependency opt-in unless the task explicitly requires it;
- establish a small, coherent source/test segregation before adding multiple new files.

## Isolation and worktrees

Use isolated Git worktrees for high/critical risk changes, long-running tasks, parallel mutating agents, experiments, or recovery from uncertain changes.

The worktree helper is:

`python .ai-harness/worktree.py create <name>`

Keep failed worktrees for inspection. Remove successful worktrees only after changes are safely preserved.

Never allow two mutating agents to edit the same files concurrently without an explicit merge strategy.

## Model routing

Use the least capable model and reasoning effort that safely solves the current phase.

- low: routing, summarization, trivial edits
- standard: normal implementation, debugging, tests
- high: architecture, hard debugging, high-risk changes
- critical: long-horizon, cross-repository, or severe production/security work

Escalate when uncertainty is unknown, risk is high/critical, verification fails repeatedly, or the task crosses significant boundaries.

## Independent review

Use read-only independent reviewers for important changes. Reviewer roles can include correctness, security, performance, reliability, architecture, compatibility, and tests.

For high-risk work prefer multiple independent lenses. Reviewers must inspect the actual repository/diff rather than trusting the implementing agent's summary. Preserve disagreements instead of averaging them away.

The reviewer helper is:

`python .ai-harness/review_agents.py --agent claude --run-dir <run> --task "..." --review correctness --review security`

Reviewers must not modify files.

## Engineering principles

Apply `.ai-harness/principles.md` and `.ai-harness/ai-coding-best-practices.md` as decision constraints, not rituals. Also consult the control-plane policies:

- `.ai-harness/ORCHESTRATION_SPEC.md`
- `.ai-harness/CONTEXT_POLICY.md`
- `.ai-harness/ARCHITECTURE_POLICY.md`
- `.ai-harness/EXECUTION_POLICY.md`
- `.ai-harness/VERIFICATION_POLICY.md`
- `.ai-harness/REVIEW_POLICY.md`
- `.ai-harness/LEARNING_POLICY.md`
- `.ai-harness/TOKEN_POLICY.md`
- `.ai-harness/PROVIDER_CONTRACT.md`
- `.ai-harness/QUALITY_GOVERNANCE.md`

## Verification gate

Before completion, verify as appropriate:

- acceptance criteria
- focused behavior tests
- build/type/lint checks
- changed contracts
- error/failure paths
- security implications
- performance implications
- compatibility and migration safety
- final diff cleanliness
- file placement and segregation consistency
- independent review findings

A model's statement that the work is complete is not evidence.

## Learning contract

After a completed run, record evidence-backed observations, route quality, verification result, useful lessons, failures, reviewer findings, model/provider choice, retries, token/tool metrics when available, naming/placement decisions, and task cost. Promote durable patterns only after repeated successful observations.

Never allow one model response to rewrite harness code, security policy, provider permissions, or permanent engineering rules automatically. Self-improvement changes knowledge and routing candidates first; durable system changes require normal review and validation.

## Token discipline

Carry conclusions, decisions, failures, open questions, checkpoints, placement decisions, and targeted evidence. Do not carry full transcripts unless required to recover missing context. Optimize repeated context preparation before reducing verification quality.

## Completion format

Return:

- outcome
- files changed
- validation evidence
- independent review evidence when used
- placement and naming decisions for new files
- existing project conventions reused
- dependency decisions, if any
- principles materially applied
- assumptions
- remaining risks
- checkpoint or follow-up when work is intentionally incomplete
