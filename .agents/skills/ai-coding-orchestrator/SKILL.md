---
name: ai-coding-orchestrator
description: Automatically determine the engineering state, required context, capabilities, risk controls, validation strategy, and token budget for prompts, tasks, Jira items, issues, and coding requests. Use the minimum workflow that safely solves the task.
---

# AI Coding Orchestrator

Invoke this skill for software-engineering requests before making changes.

## Routing contract

1. Normalize the input into task, source, Jira/issue reference, constraints, and acceptance criteria.
2. Inspect repository state and targeted context.
3. Retrieve only relevant learned patterns.
4. Classify intent, scope, risk, and uncertainty.
5. Select the minimum useful capabilities:
   - research for unknown technology, external facts, competing approaches, or architecture decisions
   - poc for feasibility or high technical uncertainty
   - grill for high-risk security, migration, performance, production, or design decisions
   - review for meaningful code changes
   - debug for failures, regressions, intermittent behavior, or root-cause work
6. Use the harness runner when execution is needed: `python .ai-harness/run.py run --task "..."`.
7. Keep context token-efficient. Prefer repository maps, targeted files, summaries, and relevant memory over full history.
8. Never claim commands, tests, Jira data, or sources that were not accessed.

## Learning contract

After a completed run, record evidence-backed lessons. Promote patterns only after repeated successful observations. Never let one model response rewrite harness code or permanent rules.

## Expected route examples

- simple edit: context -> implement -> validate -> review
- unknown library: research -> context -> implement -> validate -> review
- feasibility question: research -> poc -> learn
- intermittent production bug: context -> debug -> implement -> validate -> review
- security or migration change: research -> context -> implement -> validate -> grill -> review -> learn
- Jira feature: retrieve Jira context when an available connector/tool supports it, then route normally

## Token discipline

Use compact state between phases. Carry conclusions, decisions, failures, and open questions rather than full transcripts.