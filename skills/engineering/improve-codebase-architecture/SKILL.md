---
name: improve-codebase-architecture
description: Survey recent or high-friction areas for deepening opportunities, render a visual report, and route a selected candidate through the existing engineering flow.
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

Shape:

```json
{
  "repository": "repo-name",
  "generated_at": "ISO timestamp",
  "candidates": [
    {
      "id": "stable-id",
      "title": "Short deepening title",
      "strength": "Strong|Worth exploring|Speculative",
      "dependency": "in-process|local-substitutable|ports-and-adapters|mock",
      "files": ["path.py::Symbol"],
      "problem": "One sentence",
      "solution": "One sentence",
      "wins": ["short gain"],
      "before_mermaid": "flowchart LR ...",
      "after_mermaid": "flowchart LR ...",
      "adr": "optional ADR warning",
      "evidence_ids": ["..."],
      "context_evidence_digest": "..."
    }
  ],
  "top_recommendation": "stable-id"
}
```

Each candidate must be backed by repository evidence. Keep the set small and ranked. Do not invent a deepening merely because a pattern exists in an external framework.

## 3. Render the visual report

Render the candidate file with:

```bash
python skills/engineering/improve-codebase-architecture/render_report.py <input.json> <tmp-report.html>
```

The renderer produces a self-contained report with side-by-side before/after diagrams, recommendation badges, affected files, problem/solution, wins, and ADR warnings. Mermaid is used for graph-shaped relationships and the report layout stays intentionally lightweight.

Resolve the temp directory from `$TMPDIR`, falling back to `/tmp` (or `%TEMP%` on Windows). Never write the generated report into the repository unless the user explicitly asks.

Open the report for the user with the platform-native command when available. The report is evidence for selection, not an execution instruction.

## 4. Select and hand off

Do not implement directly from a survey candidate. When a candidate is selected, use the existing phase-boundary contract in `skills/engineering/PHASE_BOUNDARIES.md`.

Create the handoff with the canonical collaboration fabric:

```python
from .ai_harness.runtime.collaboration import build_handoff, persist_handoff
```

The handoff must carry:

- `intent_digest`
- current and requested phase
- scope and non-goals
- evidence-backed findings
- accepted decisions
- unresolved risks/questions
- repository snapshot
- context evidence digest
- artifact and verification/review receipt IDs
- parent provenance hash
- exact next action and stopping condition

Use `record_handoff(...)` with the existing `ProvenanceLedger` so the transition becomes a `phase.handoff` event in the same evidence chain. Never create another ledger.

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

The report identifies leverage. The canonical runtime executes the change.
