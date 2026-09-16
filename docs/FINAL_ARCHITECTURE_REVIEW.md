# Final v23 Architecture Review

## Review scope

Reviewed the consolidated architecture against the earlier external-audit observations and the next-stage control-loop findings: ownership overlap, repository-model duplication, context drift, execution-model duplication, portable/full-runtime ambiguity, evidence lineage, probabilistic decision handling, workflow evaluation, state determinism, adaptive learning safety, compound learning, lifecycle/version sprawl, documentation authority, multi-agent posture, and distribution duplication.

## Findings

### Resolved

- Repository truth has one canonical owner: `CodebaseIndex`; repository intelligence remains a facade/view.
- Context is derived from repository truth and now carries a deterministic snapshot/recipe fingerprint for safe reuse; hidden project configuration surfaces are indexable rather than silently discarded.
- Evidence has one canonical ledger: `engineering-state.schema.json:evidence`; `EvidenceSpine` remains validation-only.
- Decisions remain records in the canonical engineering-state ledger and can carry typed output, bounded probabilities, model identity, calibration group, abstention and observed outcome metadata.
- Planning has one canonical owner: `TaskPlan`; execution-plan compatibility remains separate and task metadata can describe parallel groups, checkpoints and verification strategy.
- Execution has one canonical engine: `StateGraph`; agent teams remain a strategy surface, with explicit join edges and cooperative cancellation while retaining deterministic merge/checkpoint semantics.
- Cross-phase identity is explicit in `ExecutionEnvelope` with versioned schema and snapshot/evidence checks.
- State graph digests use canonical JSON rather than `repr`; checkpoint digests are verified.
- Retry semantics are constrained by retryable exception classes and declared node effects; external effects are not retried by default.
- Node timeout returns control without waiting for the worker thread; parallel results retain deterministic merge order.
- Workflow evaluation is provider-neutral measurement of decision accuracy, calibration, Brier score, abstention, latency and token cost; evaluation does not authorize release or upgrade verification truth.
- Adaptive learning records task class, model, context size, latency, token cost, correction, rework and verification-failure signals and requires repeated comparable evidence before multi-agent promotion.
- Compound learning can retain reusable engineering lessons with evidence and recurrence observations while remaining advisory.
- Compatibility surfaces carry explicit status, owner, replacement and removal conditions in a machine-readable registry.
- Current architecture is separated from historical records through `ARCHITECTURE_CURRENT.md` and the compatibility policy.
- Portable/full-runtime boundaries are explicit and dependency direction is mechanically validated.
- CI publishes one canonical portable archive and validates its manifest, launcher, plugin version and artifact policy.

## Residual non-critical risks

- Python threads still cannot forcibly terminate arbitrary running user code. Cooperative cancellation now bounds future graph scheduling, while long-running in-flight work still requires cooperative node behavior or process isolation.
- Existing historical compatibility surfaces remain for backward compatibility. Their removal should follow the conditions in `architecture/compatibility.yaml`, not happen as a broad breaking cleanup.
- The execution envelope remains a contract record, not the durable state store; lifecycle persistence continues to belong to the engineering-state ledger.
- Probability calibration remains empirical: an external reference probability is optional and should be supplied by the evaluation harness when available.

## Architecture verdict

The next-stage control-loop additions extend the existing canonical spine without creating another repository graph, planner, workflow engine, evidence store, memory authority, capability catalog, or decision database. Remaining items are operational hardening opportunities rather than competing architecture authorities.
