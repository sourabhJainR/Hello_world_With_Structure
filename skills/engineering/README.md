# Composable Engineering Skills

These skills adapt the strongest process ideas from `mattpocock/skills` to this repository's existing architecture.

They are deliberately thin orchestration documents. Runtime execution, context retrieval, capability selection, bounded loops, provenance, verification, and rollout remain owned by the existing AI Coding Orchestrator and `.ai-harness` contracts.

## Flows

`ask-matt` routes work to the smallest useful capability.

`grill-with-docs -> to-spec -> to-tickets -> implement -> tdd -> code-review` is the normal idea-to-ship path when the work warrants the full flow.

`diagnosing-bugs` is the bug-fixing on-ramp.

`improve-codebase-architecture` and `codebase-design` handle architecture health and module-shape decisions.

`domain-modeling` keeps domain language and durable decisions coherent.

## Phase boundaries and handoffs

`PHASE_BOUNDARIES.md` defines the five safe phase transitions: continue, clear, handoff, subagent, and compact. It is a decision contract, not another state machine.

The canonical handoff implementation remains `.ai-harness/runtime/collaboration.py`. It now carries intent, phase transition, scope, non-goals, context evidence digest, repository snapshot, artifact/receipt IDs, parent provenance hash, verification state, and exact next action. `record_handoff(...)` writes a `phase.handoff` event to the existing `ProvenanceLedger`.

Handoffs are persisted under `.ai-harness/state/handoffs/` and must be validated against the expected intent and requested phase before consumption. Repository mutation requires fresh context after a stale snapshot is detected.

## Visual architecture reviews

`improve-codebase-architecture` produces a bounded candidate JSON and renders a self-contained HTML report with before/after diagrams using `skills/engineering/improve-codebase-architecture/render_report.py`.

The report is evidence for selection. A selected candidate does not execute directly; it is handed into the normal design/spec/ticket/implementation/verification/review flow through the same provenance chain.

## Ownership rule

Do not duplicate the repository's planner, memory, context, capability registry, feedback loop, provenance ledger, verification receipts, or release state inside these skills. Skills select and constrain work; the canonical runtime executes it.
