# Evidence, review, rollout, and safety

Evidence must be traceable and sufficient for the claim. Verification is independent of generation; review gates the verified artifact and the same evidence.

## Bug path

`reproduce -> isolate -> identify owner -> minimal fix -> regression test -> verify -> review adjacent behavior`

## Deployment lineage

Use:

`research -> plan -> implement -> verify -> review -> integrate -> regression -> shadow -> canary -> promote`

Rollback after a failed gate. Never bypass security, permission, scope, or regression gates. Require explicit approval for destructive, irreversible, production, financial, privacy-sensitive, or external-message actions.

## Review discipline

Acquire enough context to inspect contracts and dependency graph. Reproduce reported behavior, classify findings, course-correct only at the source of the problem, and verify adjacent behavior. Review the artifact against the same evidence used to establish correctness.

## Safety boundaries

Keep permissions, scope, lifecycle, and ownership explicit. Do not silently widen access, introduce an alternate control plane, or make an irreversible action through an implicit fallback. Preserve auditability and durable state where the surrounding system already provides it.
