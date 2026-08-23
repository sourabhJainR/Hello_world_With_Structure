---
name: ai-coding-orchestrator
description: Automatically determine the engineering state, required context, capabilities, risk controls, verification strategy, model/tool budget, and stopping condition for prompts, tasks, Jira items, issues, and coding requests. Use the minimum safe workflow that achieves a verified outcome.
---

# AI Coding Orchestrator

Invoke this skill for every non-trivial software-engineering request before making changes.

## Operating contract

1. Normalize the input into task, source, Jira/issue reference, constraints, acceptance criteria, non-goals, and stopping condition.
2. Inspect repository state, applicable instructions, nearby patterns, dependency boundaries, and relevant tests.
3. Retrieve only relevant learned patterns and current evidence.
4. Classify intent, scope, risk, uncertainty, change surface, and reversibility.
5. Select the minimum useful capabilities and model/tool budget.
6. Execute in a controlled loop: understand -> plan -> change -> verify -> inspect diff -> review -> learn.
7. On failure, diagnose before retrying. Every retry must add new evidence or change the approach.
8. Persist a checkpoint for long-running or interrupted work so another session can resume without replaying the full transcript.
9. Stop when acceptance criteria are satisfied and evidence supports completion.
10. Never claim commands, tests, Jira data, source material, or tool usage that did not occur.

## Automatic capability routing

- `research`: unknown technology, external facts, current documentation, competing approaches, architecture decisions
- `poc`: feasibility questions, unresolved technical uncertainty, experiments that should precede production changes
- `debug`: failures, regressions, intermittent behavior, root-cause analysis
- `grill`: meaningful security, migration, performance, production, reliability, or high-risk design work
- `review`: meaningful changes, release-impacting changes, or explicit review requests
- `validate`: build, type, lint, tests, integration checks, static analysis, migration checks, and other repository-native evidence
- `learn`: extract evidence-backed lessons and task metrics after completion

Skip capabilities when repository evidence makes them unnecessary. Do not run every capability on every task.

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

For AI-specific work also apply lean prompts, explicit success criteria, bounded tool sets, minimum capable model/reasoning effort, structured checkpoints, controlled delegation, verification gates, and evidence-based learning. These align with current agent guidance emphasizing lean prompts, explicit stopping criteria, relevant tools, deliberate reasoning effort, context management, and safe multi-agent delegation. citeturn817632search0turn817632search2

## Context engineering

Use the stable context prefix first:

1. repository instructions
2. principles and task contract
3. compact repository map
4. relevant learned memory
5. current task and acceptance criteria

Then add phase-specific evidence only.

Prefer targeted searches and summaries over full repository dumps or full previous transcripts. Preserve stable prefixes so providers that support caching can reuse them.

## Model and tool routing

Use the least capable model and reasoning effort that can safely solve the current phase. Escalate when:

- uncertainty is high
- debugging remains unresolved
- security or production risk is high
- changes cross boundaries or repositories
- verification fails repeatedly
- the task becomes long-horizon or highly coupled

Expose only the tools needed for the phase. Use read-only investigation before mutation when possible. Prefer isolated worktrees or sandboxes for risky or parallel work.

## Delegation

Delegate only work that is genuinely independent: parallel repository investigations, alternative design research, independent reviews, test planning, or security review. Do not delegate simultaneous edits to the same files without an explicit merge plan.

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

A model's statement that the work is complete is not evidence.

## Learning contract

After a completed run, record evidence-backed observations, route quality, verification result, useful lessons, failures, and token/tool metrics when available. Promote durable patterns only after repeated successful observations.

Never allow one model response to rewrite harness code, security policy, provider permissions, or permanent engineering rules automatically. Self-improvement changes knowledge and routing candidates first; durable system changes require normal review and validation.

## Expected route examples

- simple edit: context -> implement -> validate -> review
- small bug: context -> debug -> implement -> validate -> review
- unknown library: research -> context -> implement -> validate -> review
- feasibility question: research -> poc -> validate -> learn
- intermittent production bug: context -> debug -> implement -> validate -> review -> learn
- security or migration change: research -> context -> implement -> validate -> grill -> review -> learn
- Jira feature: retrieve available Jira context, normalize acceptance criteria, then route normally

## Token discipline

Carry conclusions, decisions, failures, open questions, checkpoints, and targeted evidence. Do not carry full transcripts unless required to recover missing context.

## Completion format

Return:

- outcome
- files changed
- validation evidence
- principles materially applied
- assumptions
- remaining risks
- checkpoint or follow-up when work is intentionally incomplete
