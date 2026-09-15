---
name: improve-codebase-architecture
description: Survey recent or high-friction areas for deepening opportunities, render evidence-backed visual documentation, and route a selected candidate through the existing engineering flow.
disable-model-invocation: true
---

# Improve Codebase Architecture

This skill is a read-only survey followed by a deliberate handoff into normal engineering work. It does not silently refactor production code.

## 1. Explore

Start with a user-named direction when provided. Otherwise inspect recent commit hotspots and recurring changes first. Use repository structure, symbols, dependency/graph evidence, tests, ADRs, and `CONTEXT.md`.

For each candidate apply the deletion test: would deleting or deepening the module concentrate complexity rather than move it?

Look for:

- shallow modules whose interface nearly matches their implementation;
- behavior that requires unnecessary hops across modules;
- callers coupled to internal data or lifecycle mechanics;
- missing seams that make behavior hard to verify;
- repeated edits around one responsibility;
- abstractions that add indirection without enough depth.

Do not re-litigate an ADR unless there is concrete friction worth reopening.

## 2. Build candidate data

Create a bounded JSON candidate file in the OS temp directory. Do not mutate repository source during this phase.

Each candidate must be backed by repository evidence. Keep the set small and ranked. Do not invent a deepening merely because a pattern exists in an external framework.

## 3. Render interactive documentation

For a visual artifact, hand the evidence-backed candidate data to `interactive-documentation`.

Use:

```bash
python skills/engineering/interactive-documentation/render_document.py <input.json> <tmp-report.html>
```

The input should contain stable node IDs, authored edges, source paths/symbols, evidence IDs, snapshot digest, unknowns, and optional named views. The renderer produces one self-contained HTML file with search, focus, relationship tracing, theme switching, evidence details, keyboard navigation, and print-friendly output.

The artifact must not depend on CDN scripts, remote fonts, telemetry, or a hosted viewer. Resolve the temp directory from `$TMPDIR`, falling back to `/tmp` (or `%TEMP%` on Windows). Never write the generated report into the repository unless the user explicitly asks.

The report is evidence for selection, not an execution instruction. Visual proximity is not runtime reachability and an authored graph edge is not test coverage.

## 4. Select and hand off

Do not implement directly from a survey candidate. When a candidate is selected, use the existing phase-boundary contract in `skills/engineering/PHASE_BOUNDARIES.md`.

Create the handoff with the canonical collaboration fabric and existing provenance ledger. The handoff must carry intent, phase, scope, non-goals, evidence-backed findings, accepted decisions, unresolved risks, repository snapshot, context evidence digest, artifact and receipt IDs, parent provenance hash, exact next action, and stopping condition.

If the repository changed since the candidate report, acquire fresh context before design or implementation. The report is not a substitute for current context.

## 5. Continue through normal engineering flow

A selected architecture candidate re-enters the normal path:

`phase handoff -> grill/design -> spec -> tickets -> implement -> TDD where applicable -> verify -> two-axis review -> artifact -> rollout`

Use `codebase-design` for interface/seam decisions. Use `domain-modeling` when the candidate changes domain vocabulary. Use `tdd` at the agreed behavioral seam. Use `code-review` after implementation.

Every meaningful transition retains the same intent and evidence lineage.

## Scope discipline

This skill is a survey plus a selection/handoff mechanism. It must not:

- add a second planner or memory store;
- create parallel execution or release state;
- silently change interfaces during the survey;
- treat an HTML report as proof of correctness;
- bypass verification, review, security, approval, or rollout gates.

The visual document explains the evidence. The canonical runtime executes the change.
