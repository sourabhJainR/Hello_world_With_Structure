---
name: ai-coding-orchestrator
description: Repository-aware AI coding workflow for research, implementation, review, verification, visual documentation, and safe rollout.
---

# AI Coding Orchestrator

Use the repository as the source of truth. Keep work bounded, evidence-backed, deterministic where possible, compatible, and easy to verify. The orchestrator facilitates work; it does not create a second intelligence or ownership layer.

## Start here

For structural, cross-file, unfamiliar, or risk-sensitive tasks, start with the repository map, then retrieve only the context needed for the task. Prefer one capable agent first; add coordination only when independence, prior failure, measurable benchmark value, or a clear safety boundary justifies it.

```bash
python -m portable.repo_intelligence . --for="<task>" --token-budget=4000
```

Use focused map queries for callers, callees, impact, tests, and current situational state. Treat the map as evidence acceleration, not proof; retain its digest, confidence, skipped files, parse errors, and unknowns.

## Contract anchors

`portable.task_planner.TaskPlan`, `portable.impact_analysis`, `portable.repo_intelligence.RepositoryMap`, `CodebaseIndex`, `ContextEvidence` and `.ai-harness/runtime/tool_runner.py`, `.ai-harness/runtime/lsp_server.py`, `.ai-harness/runtime/feedback_loop.py`, `.ai-harness/runtime/auto_compaction.py` remain canonical. `downgrade=explicit_install_only` applies to artifact installation.

## Required workflow

`intent -> context -> plan -> evidence -> change -> verification -> review -> artifact -> rollout -> observation`

For code changes, make reuse, compatibility, data/DB access, performance, logging/telemetry, exception handling, and regression evidence explicit. Prefer existing implementations and established contracts over duplication.

Read the detailed guidance before substantial implementation:

- [Retrieval and context](references/01-retrieval-context.md)
- [Engineering quality and reuse](references/02-engineering-quality.md)
- [Runtime contracts and chat trigger](references/03-runtime-contracts.md)
- [Evidence, review, rollout, and safety](references/04-evidence-rollout.md)
- [Working sequences and output discipline](references/05-working-sequence.md)

## Rules that always apply

Prefer minimal safe changes. Do not create parallel repository indexes, memory stores, capability catalogs, evidence stores, workflow engines, logging abstractions, or privileged paths. Preserve existing API shapes, lifecycle ordering, persisted contracts, CLI/HTTP behavior, and user-visible workflows unless the requested change explicitly requires a contract change.

For bugs: `reproduce -> isolate -> identify owner -> minimal fix -> regression test -> verify -> review adjacent behavior`.

Require explicit approval for destructive, irreversible, production, financial, privacy-sensitive, or external-message actions. Never bypass security, permission, scope, or regression gates.

Skills are orchestration surfaces and `skills are orchestration surfaces` that reuse canonical repository, context, evidence, and provenance stores. `interactive-documentation` remains a composed skill using canonical evidence and provenance.
