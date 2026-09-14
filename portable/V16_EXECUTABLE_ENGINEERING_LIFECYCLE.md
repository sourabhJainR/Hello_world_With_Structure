# V16 — executable engineering lifecycle

AER now treats review as a first-class evidence-bound gate and provides a provider-neutral team coordinator for splitting substantial work into independently complete units.

## Complete lifecycle

```text
research
  -> plan
  -> implement
  -> verify
  -> review
  -> shadow
  -> canary
  -> promote
       \-> rollback on failed observation/gate
```

The same `ContextEvidence.evidence_digest` is carried through the engineering and rollout stages. Verification produces a `VerificationReceipt` bound to the artifact and evidence. Review produces a `ReviewReceipt` bound to the same artifact, evidence, and verification. Promotion requires both receipts and requires the artifact to have passed through canary.

## Early course correction

`portable.agency_team_orchestrator.AgentTeamOrchestrator` is deliberately a coordinator, not a model runtime. The host supplies `spawn`, `verify`, and `review` callbacks.

A team is represented as `WorkUnit`s with:

- a complete unit goal;
- a specialist/role;
- read/write resources;
- explicit dependencies;
- mutation mode and priority.

The coordinator then:

1. builds the existing conflict-aware execution plan;
2. spawns independent read-only units in bounded parallel waves;
3. serializes mutating work;
4. runs verification immediately after each unit completes;
5. runs review immediately after verification;
6. stops failed units and their dependents instead of spending tokens on work that cannot safely continue;
7. preserves the same evidence digest for every spawned agent;
8. returns deterministic unit gates and a team digest.

This makes verification and review a feedback mechanism during implementation rather than a final ceremony after all work is finished.

## Host integration boundary

```python
run = AgentTeamOrchestrator(max_parallel=4).run(
    units,
    evidence_digest=context_evidence.evidence_digest,
    spawn=host.spawn_agent,
    verify=host.verify_unit,
    review=host.review_unit,
)
if not run.passed:
    # course-correct the failed unit; do not continue its dependents
    ...
```

The host remains responsible for model/provider selection, command execution, sandboxing, credentials, permissions, and external side effects. AER owns planning, evidence identity, conflict boundaries, gate semantics, and release lineage.

## Release integration

```python
release = bind_release_context(store_root, context_evidence)
verification = release.verify(artifact, {"unit_tests": True, "static_checks": True})
review = release.review(artifact, verification)
release.shadow(artifact, review=review)
release.canary(artifact, review=review)
release.promote(artifact, verification=verification, review=review)
```

A missing review receipt, mismatched evidence, mismatched verification, unresolved finding, skipped shadow, or skipped canary fails closed. Rollback remains available for failed rollout observations.

## Design intent

The implementation reuses the existing `agency_execution_plan`, `ContextEvidence`, `ArtifactStore`, verification, regression, and provenance contracts. It does not introduce a second retrieval engine, memory store, specialist registry, or agent runtime.
