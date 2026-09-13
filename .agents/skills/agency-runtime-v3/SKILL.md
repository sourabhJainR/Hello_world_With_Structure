# Agency Runtime v3

Use this skill for substantial specialist-agent work where the output must be auditable and release-safe.

## Operating contract

1. Build a `TaskProfile` with task id, artifact type, risk, mutation mode, acceptance criteria, evidence requirements, and technologies.
2. Route deterministically and explainably. Select one primary specialist; add support or an independent reviewer only when it can change the result.
3. Keep conflicting mutations serialized. Read-only evidence collection may be parallelized by the host implementation.
4. Require structured deliverables, evidence, verification, quality dimensions, and hard-gate results from the worker.
5. Record provenance for material claims and evidence. Never put secrets or credentials into the ledger.
6. Evaluate the result through the deterministic quality runtime. A specialist cannot self-certify release readiness.
7. Material/blocker findings require repair and re-verification. Repair cycles must have a hard upper bound.
8. If evidence, verification, acceptance, or permissions are insufficient, stop with a failed/blocked receipt rather than reporting success.

## Failure boundaries

- Do not expand scope without an explicit task change.
- Do not treat model text as evidence of execution.
- Do not claim tests, builds, deployments, reviews, or external actions that were not recorded.
- Do not run arbitrary commands merely to satisfy a quality field; verification must be performed by the host execution layer.

## Output

Return the final deliverables, evidence references, verification summary, findings, deterministic quality receipt, and provenance ledger. The caller should expose uncertainty and unresolved risks rather than hiding them.
