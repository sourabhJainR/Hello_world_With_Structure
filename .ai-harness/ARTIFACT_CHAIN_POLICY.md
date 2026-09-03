# AI-Native SDLC Artifact Chain

The harness uses a run-scoped artifact chain to make intent durable, machine-actionable, and reviewable:

`intent.md -> spec.md -> plan.md -> changeset -> verification -> review -> proof`

## intent.md

The immutable human/task intent is the source of truth. It captures the goal, why, requirements, acceptance criteria, guardrails, boundaries, and non-goals. The intent digest is persisted so later phases can detect drift.

For materially ambiguous requests, the harness should clarify before mutation. The clarification response is `CLARIFICATION_NEEDED` with only the highest-value questions.

## spec.md

The specification is derived from intent and translates it into functional requirements and acceptance conditions. It may become more precise from repository evidence, but cannot silently broaden or contradict intent, security policy, compatibility requirements, or approval rules.

## plan.md

The plan records the execution sequence and completion gate. Agents may refine sequencing when evidence requires it. The goal, acceptance criteria, guardrails, and non-goals remain immutable.

## Governance

- Repository instructions and security policy outrank model suggestions.
- Human approval remains required for destructive, production-external, permission, and security-policy changes.
- AI-generated repository changes remain staged/isolated until an authorized human or CI policy commits and pushes them.
- Verification is deterministic and authoritative; model confidence is not proof.
- Every artifact is run-scoped and hashed where practical for auditability.
- Interesting but out-of-scope findings become deferred work rather than scope expansion.

The artifact chain is a framework, not a rigid workflow. Workflows may skip or add phases when the task contract requires it, but must preserve traceability from intent to evidence and outcome.
