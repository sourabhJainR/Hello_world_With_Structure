# Composable Engineering Skills

These skills adapt the strongest process ideas from `mattpocock/skills` to this repository's existing architecture.

They are deliberately thin orchestration documents. Runtime execution, context retrieval, capability selection, bounded loops, provenance, verification, and rollout remain owned by the existing AI Coding Orchestrator and `.ai-harness` contracts.

## Flows

`ask-matt` routes work to the smallest useful capability.

`grill-with-docs -> to-spec -> to-tickets -> implement -> tdd -> code-review` is the normal idea-to-ship path when the work warrants the full flow.

`diagnosing-bugs` is the bug-fixing on-ramp.

`improve-codebase-architecture` and `codebase-design` handle architecture health and module-shape decisions.

`domain-modeling` keeps domain language and durable decisions coherent.

## Ownership rule

Do not duplicate the repository's planner, memory, context, capability registry, feedback loop, provenance ledger, verification receipts, or release state inside these skills. Skills select and constrain work; the canonical runtime executes it.
