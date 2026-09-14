# Executable context/evidence lifecycle

The coding runtime now acquires one immutable `ContextEvidence` envelope and carries its identity through execution and deployment.

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
release.promote(artifact)
# if observations fail:
release.rollback()
```

Each executable transition writes the same evidence digest into the release reason/audit trail. This prevents a rollout decision from being detached from the context that produced it.

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
      +--> implement / review / verify
      |
      +--> shadow --same E--> canary --same E--> promote
      |                         |
      |                         +--> failure --same E--> rollback
      |
      +--> audit / policy / release history
```
