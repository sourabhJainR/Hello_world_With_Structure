# Reference Applications

These examples are intentionally outside the core orchestration runtime. They demonstrate ordinary software that can be built, reviewed, researched, and evolved using the orchestrator.

They are not dependencies, fixtures, or required runtime components.

## Included references

| Example | Purpose | Control-plane coverage |
| --- | --- | --- |
| `habit-tracker/` | Small CRUD-style application showing tasks, streaks, validation, and tests. | Complete-job prompting, material ambiguity, scope fencing, script-first validation, deterministic proof. |
| `family-financial-register/` | Offline continuity-oriented record structure using fake data only. | Complete-job prompting, material ambiguity, security/scope fences, script-first validation, deterministic proof. |

Each example keeps domain code independent from `.ai-harness`. The harness scenarios live in `HARNESS_SCENARIOS.md` within the example and describe the expected run behavior without coupling the application to the control plane.

## Current reference pattern

A good example task should exercise the same contract used by the current implementation:

1. **Intent** — immutable user outcome, rationale, done criteria, guardrails, and non-goals.
2. **Spec** — refine the requested behavior without silently broadening intent.
3. **Plan** — sequence the work and identify deterministic checks.
4. **Changeset** — make only the authorized change.
5. **Verification** — use deterministic tests/scripts as the authoritative check.
6. **Review** — inspect the result for correctness, scope, security, and regressions.
7. **Proof** — retain evidence tied to the run and final changeset.

The scenarios also demonstrate `CLARIFICATION_NEEDED` for material ambiguity, explicit scope fencing for out-of-scope work, script-first handling of repeatable mechanical tasks, and human approval for destructive or security-sensitive changes.

Run either example directly from its directory with the documented Python test command. These examples require no external services and use no real credentials or secrets.
