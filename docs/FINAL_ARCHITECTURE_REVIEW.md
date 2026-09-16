# Final v23 Architecture Review

## Review scope

Reviewed the consolidated architecture against the earlier external-audit observations: ownership overlap, repository-model duplication, execution-model duplication, portable/full-runtime ambiguity, evidence lineage, state determinism, adaptive learning safety, lifecycle/version sprawl, documentation authority, multi-agent posture, and distribution duplication.

## Findings

### Resolved

- Repository truth has one canonical owner: `CodebaseIndex`; repository intelligence is a facade/view.
- Evidence has one canonical ledger: `engineering-state.schema.json:evidence`; `EvidenceSpine` is validation-only.
- Planning has one canonical owner: `TaskPlan`; execution-plan compatibility is classified separately.
- Execution has one canonical engine: `StateGraph`; agent teams remain a strategy surface.
- Cross-phase identity is explicit in `ExecutionEnvelope` with versioned schema and snapshot/evidence checks.
- State graph digests use canonical JSON rather than `repr`; checkpoint digests are verified.
- Retry semantics are constrained by retryable exception classes and declared node effects; external effects are not retried by default.
- Node timeout returns control without waiting for the worker thread; parallel results retain deterministic merge order.
- Adaptive learning records task class, model, context size, latency, token cost, correction, rework, and verification failure signals and requires repeated comparable evidence before multi-agent promotion.
- Compatibility surfaces carry explicit status, owner, replacement, and removal conditions in a machine-readable registry.
- Current architecture is separated from historical records through `ARCHITECTURE_CURRENT.md` and the compatibility policy.
- Portable/full-runtime boundaries are explicit and dependency direction is mechanically validated.
- CI publishes one canonical portable archive and validates its manifest, launcher, plugin version, and artifact policy.

## Residual non-critical risks

- Python threads cannot forcibly terminate arbitrary running user code. The timeout contract bounds caller wait and cancels queued work; long-running in-flight work requires cooperative cancellation or a process-isolated adapter.
- Existing historical compatibility surfaces remain for backward compatibility. Their removal should follow the conditions in `architecture/compatibility.yaml`, not happen as a broad breaking cleanup.
- The execution envelope is intentionally a contract record, not the durable state store; integrations must continue using the engineering-state ledger for lifecycle persistence.

## Architecture verdict

The audited structural conflicts are addressed without introducing another repository graph, workflow engine, evidence store, memory authority, capability catalog, or planner. Remaining items are operational hardening opportunities rather than competing architecture authorities.
