# Execution Contract

## Purpose

`portable.execution_contract.ExecutionEnvelope` is the canonical cross-phase contract for one engineering execution. It carries identity and provenance across intent, repository facts, planning, execution, verification, review, regression, release, outcome, and learning without introducing another state store.

## Canonical fields

- `intent`: task identity, goal, and explicit non-goals.
- `repository`: the exact `CodebaseIndex` digest used to prepare context.
- `plan`: the canonical `TaskPlan` identity and task IDs in scope.
- `evidence`: evidence IDs plus snapshot/freshness boundaries.
- `decisions`: compact decision records; source evidence remains elsewhere.
- `changeset_id`: identity of the produced repository change.
- `verification_ids`, `review_ids`, `regression_ids`, `release_ids`: lifecycle receipt references.
- `metadata`: bounded non-authoritative execution metadata.

## Invariants

1. The repository reference must name the canonical `CodebaseIndex` and a non-empty digest.
2. A non-empty plan task list must contain the envelope task ID.
3. Evidence IDs are unique within an envelope.
4. Serialization is canonical and stable; the envelope digest is content-addressed.
5. The envelope is a contract record, not a replacement for the engineering state ledger, repository model, evidence store, or release gate.
6. Learning may attach observations or recommendations but cannot use the envelope to authorize permissions or bypass verification/release controls.

## Staleness boundary

A repository or evidence digest is an execution input, not a timeless fact. Before resuming work after a repository mutation or a stale handoff, the caller must refresh the canonical model/evidence and construct a new envelope rather than silently reusing an obsolete digest.

## Distribution contract carried forward

The portable runtime is distributed as one canonical `aer-portable.zip`. The archive contains the `aer_cli.py` launcher and `aer-bundle.json` integrity manifest at its root; the launcher is itself integrity-covered. CI publishes that single archive and verifies plugin/bundle version consistency from the canonical payload.
