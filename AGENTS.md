# Repository AI Agent Instructions

This repository uses an adaptive, provider-neutral AI coding orchestrator.

## Default behavior

For every non-trivial software task, first infer the required engineering state from the prompt, task, Jira/issue reference, repository state, risk, and uncertainty. Use the minimum safe workflow. Do not make the user choose Research, POC, Grill, Debug, Review, or other capabilities manually unless they ask for a specific mode.

The canonical skill is:

`.agents/skills/ai-coding-orchestrator/SKILL.md`

The executable harness is:

`python .ai-harness/run.py`

## Automatic capability routing

- research: unknown technology, external facts, competing options, architecture decisions
- poc: feasibility or unresolved technical uncertainty
- debug: failures, regressions, intermittent behavior, root-cause analysis
- grill: meaningful security, migration, performance, production, or high-risk design work
- review: meaningful code changes and release-impacting changes

Skip optional capabilities when repository evidence already makes them unnecessary.

## Context and tokens

Use repository maps and targeted file reads. Carry compact summaries, decisions, failures, and open questions rather than full transcripts. Retrieve only relevant learned memory.

## Learning

Every completed run may contribute evidence-backed lessons to `.ai-harness/memory/`. Lessons are promoted only after repeated successful observations. Never allow one model response to modify harness code or permanent rules automatically.

## Coding rules

- Inspect before changing code.
- Prefer the smallest correct change.
- Reuse existing patterns and dependencies.
- Do not modify unrelated files.
- Add or update focused tests.
- Preserve compatibility unless the task says otherwise.
- Never claim commands, tests, Jira data, or research sources that were not accessed.

## Completion

Report what changed, files changed, validation performed, important assumptions, and remaining risks.