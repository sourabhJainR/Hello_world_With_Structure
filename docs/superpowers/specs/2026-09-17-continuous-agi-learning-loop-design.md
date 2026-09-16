# Continuous AGI-Aligned Learning Loop Design

## Goal

Make the deferred learning lane continuously scheduled and turn accumulated task experience into empirically validated strategy, confidence-calibration, and iteration-efficiency improvements that become available to subsequent tasks without mutating an active task.

## Design

### 1. Continuous maintenance lane

Use the existing durable `AutomationScheduler` as the single scheduling authority. Register one idempotent learning-maintenance schedule per project. Each maintenance cycle is claim-before-run and bounded by a configurable job/benchmark budget.

A cycle performs:

`claim -> drain deferred outcomes -> consolidate durable memories -> ingest benchmark history -> evaluate candidate adaptations -> update policy/thresholds -> write maintenance receipt -> finish/reschedule`

The active execution path only records an outcome and reads already-promoted guidance. It never performs consolidation or policy mutation synchronously.

A durable maintenance receipt records cycle id, project, jobs processed, memories consolidated, benchmark observations, strategy decisions, threshold changes, regressions, failures, and an evidence digest. A failed cycle is retryable and never blocks normal execution.

### 2. Experience-to-capability learning

Every completed task creates an immutable learning observation containing task family/capability, strategy/policy version, quality, iterations, confidence, verification/evidence, prediction outcomes when present, environment fingerprint, and transfer key where available.

Observations are linked to existing cognitive memory and learning structures. Consolidation extracts repeated successful and failed patterns into higher-level reusable guidance. Transfer to a distinct task/capability is weighted as stronger evidence than repetition on the identical task shape.

Learning artifacts are versioned and provenance-linked; raw observations are never rewritten by consolidation.

### 3. Long-running benchmark history

Add an append-only benchmark history store with records for task/capability, case family, policy version, score, confidence, iterations, verification/evidence ids, environment fingerprint, round, and whether the case belongs to baseline, adaptation, transfer, or holdout evaluation.

Maintain both:

- a rolling adaptation window for current workload behavior;
- a longer longitudinal/transfer window that prevents short-term workload changes from erasing durable capabilities.

Tuning decisions are derived only from observations available before the decision cutoff. A later holdout/transfer sample validates the resulting policy.

### 4. Empirical strategy tuning

Treat strategies as versioned policies. Candidate policies may be derived from consolidated patterns, prior successful experiences, or bounded counterfactual evaluations.

A candidate can become active only when it demonstrates repeated benefit across independent benchmark rounds without unacceptable regression in quality, verification, safety, or transfer performance. Improvements confined to a single task family remain scoped to that family.

Policy changes use the existing observe -> score -> replay/shadow -> canary -> promote/rollback pattern where possible. New policy versions affect only future tasks.

### 5. Confidence calibration

Track predicted confidence alongside realized outcome. Estimate calibration error over the rolling and longitudinal windows. Apply bounded calibration adjustments only when the evidence minimum is met and the proposed change is validated on holdout data.

Calibration is separated from raw task quality: a high-quality strategy with overconfident predictions is not treated as well calibrated. Confidence adjustments are incremental and capped so sparse experience cannot push confidence toward certainty.

### 6. Iteration-efficiency tuning

Maintain a learned iteration target per task family/capability plus a safe global floor/ceiling. Search for lower iteration budgets only where historical evidence shows stable quality and verification with fewer iterations.

Each accepted reduction requires repeated independent evidence and holdout validation. Any meaningful quality or verification regression blocks the reduction and restores the previous policy/threshold. Iteration tuning never trades away hard acceptance or safety requirements.

### 7. Continual self-improvement invariant

Each use participates in the loop:

`execute -> observe -> persist -> consolidate -> abstract -> hypothesize -> evaluate -> adapt -> transfer -> execute`

There is no requirement for a manually triggered retraining event for ordinary learning. The next eligible maintenance cycle processes the most recent completed outcomes. The next task can consume verified prior learning through guidance.

This is continual adaptation, not unrestricted self-modification: the execution authority, safety/quality gates, and rollback boundaries remain fixed.

### 8. Anti-feedback-loop boundaries

- Active execution cannot consume a policy version created from its own outcome.
- Tuning data and holdout validation data are separated by decision cutoff.
- Benchmark cases used to derive a threshold cannot also be the sole evidence used to validate that threshold.
- Policy/threshold changes are immutable, versioned records.
- Regressions trigger rollback or retention of the prior policy.
- No single success or failure is sufficient to materially change a strategy or threshold.

### 9. Failure handling and resource bounds

Maintenance is best-effort and resumable. Individual learning jobs that fail remain pending for retry; a poison job is isolated and eventually recorded as failed without blocking the queue. Benchmark work is budgeted per cycle so backlog cannot monopolize the scheduler.

The maintenance schedule is idempotently registered and can safely be invoked by multiple application instances because scheduler claim semantics serialize ownership of an execution slot.

### 10. Testing requirements

Tests must cover:

- idempotent maintenance schedule registration;
- single-claim execution and retry behavior;
- append-only benchmark history;
- consolidation and guidance propagation after every use;
- minimum-evidence gates for tuning;
- strategy promotion and rollback;
- confidence calibration under under-confidence and over-confidence histories;
- iteration-target reduction without quality regression;
- holdout/transfer separation;
- bounded policy changes and version provenance;
- deterministic maintenance receipts/digests;
- maintenance isolation from the active execution path.

The existing deterministic harness and all repository-required GitHub Actions checks remain release gates.

## Success criteria

1. A completed task is durably queued for learning without extending the active execution critical path.
2. Continuous maintenance automatically drains the queue and records auditable receipts.
3. Repeated experience becomes reusable guidance and can transfer to distinct tasks.
4. Long-running benchmark history empirically changes strategy selection, confidence calibration, and iteration targets only when evidence supports it.
5. Regression or weak evidence prevents promotion and preserves the prior behavior.
6. Improvements are visible to subsequent tasks without manual retraining.
