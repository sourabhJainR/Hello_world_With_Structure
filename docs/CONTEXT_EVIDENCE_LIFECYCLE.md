# Executable context/evidence lifecycle

The coding runtime acquires one immutable `ContextEvidence` envelope and carries its identity through execution and deployment.

## Pipeline

```text
intent
  -> context plan
  -> semantic retrieval
  -> symbol resolution
  -> graph expansion
  -> evidence scoring/budgeting
  -> context broker lease
  -> ContextEvidence
```

Implementation: `.ai-harness/runtime/context_pipeline.py`.

The pipeline reuses the canonical `RepositoryIntelligence`, `CodebaseIndex`, `SymbolLocator`, `context_planner`, and `context_broker`. It does not create another repository index or evidence store.

`ContextEvidence` contains:

- intent digest
- context-plan digest
- repository snapshot digest
- selected paths and semantic symbol references
- graph paths
- bounded evidence items
- one evidence digest
- unknowns and token estimate

The evidence digest is the stable lineage key for the rest of the turn.

## Deployment binding

The same envelope can be supplied to shadow and canary evaluation:

```python
shadow = evaluate_shadow(candidate, cases, runner, context_evidence=evidence)
canary = evaluate_canary(candidate, cases, runner, context_evidence=evidence)
```

Every report and staged canary record carries `context_evidence_digest`.

For artifact rollout, use `portable.context_bound_release.ContextBoundRelease`:

```python
release = ContextBoundRelease(store, evidence)
release.shadow(artifact)
release.canary(artifact)
verification = release.verify(artifact, {
    "unit_tests": True,
    "policy_check": True,
})
release.promote(artifact, verification=verification)
# if observations fail:
release.rollback()
```

`verify()` creates a content-addressed `VerificationReceipt` from the artifact digest, the same context evidence digest, and the passed checks. `promote()` validates that receipt belongs to both the artifact and evidence before accepting it.

Every executable transition writes the evidence digest as a structured release field. Verification also carries its own digest. This gives the lifecycle a concrete `build -> verify -> ship` gate instead of recording verification only as prose.

Policy records also retain `context_evidence_digest`, so promotion and rollback can be traced back to the evidence envelope.

## State rule

A rollout may change state, but it must not silently change context identity. If fresh repository context is required, call `ContextAcquisitionPipeline.refresh()` and acquire a new envelope; do not mutate the existing one.

This gives the runtime a concrete lineage:

```text
research/investigate
      |
      v
 ContextEvidence #E
      |
      +--> implement / review
      |          |
      |          v
      |       verify #V (artifact + E)
      |          |
      |          v
      +--> shadow --same E--> canary --same E + V--> promote
      |                         |
      |                         +--> failure --same E--> rollback
      |
      +--> audit / policy / release history
```
