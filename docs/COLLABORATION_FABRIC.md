# Collaboration Fabric

The harness components collaborate through a small, evidence-first memory and handoff contract.

## Rules

1. The immutable intent digest travels with every handoff.
2. A component may consume shared memory, but cannot silently change intent or guardrails.
3. Facts, evidence and decisions must retain provenance.
4. Handoffs carry findings, decisions, open risks and next actions.
5. Out-of-scope findings are deferred, not pulled into the current task.
6. Trusted DO/DON'T patterns are advisory context, never autonomous policy rewrites.
7. RCA remains analysis-only; its findings can feed learning and a later implementation task, but do not create a patch automatically.

## Component chain

Intent Contract
  -> Execution Controls
  -> Repository / Legacy Analysis
  -> RCA or Planning
  -> Implementation
  -> Verification
  -> Outcome
  -> Learning
  -> Shared Memory
  -> Next Task

Components can also form a graph: evidence supports findings, findings support decisions, and decisions are handed to the next component with the same intent digest.

## Handoff

A valid handoff contains:

- intent digest
- source and destination component
- phase
- evidence-backed findings
- decisions
- open risks
- next actions

A receiver validates the handoff before using it. Intent mismatch or scope drift is rejected.

## Memory safety

Shared memory is bounded and provenance-aware. Learning may improve retrieval and advice, but it cannot silently alter permissions, security rules, architecture policy, repository rules or executable harness behavior.

## CI contract

The collaboration fabric is covered by the repository harness gate together with intent preservation, execution controls, learning, RCA, and deterministic evaluations.
