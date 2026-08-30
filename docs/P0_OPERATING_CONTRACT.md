# P0 Operating Contract

This document turns the P0 roadmap into executable behavior.

## 1. Engineering State Ledger

Canonical schema: `state/engineering-state.schema.json`.

Rules:

- state is versioned;
- evidence is immutable once recorded;
- decisions reference evidence IDs;
- verification references evidence IDs where possible;
- outcomes reference evidence IDs where available;
- compaction may summarize state but must retain identifiers and provenance;
- secrets, credentials, tokens, and unnecessary personal data must not enter durable state;
- state transitions must be explicit; cancellation, failure, and partial completion are not success;
- concurrent agents must merge by IDs and reject conflicting decisions rather than silently overwrite them.

## 2. Evidence Contract

Material claims use an evidence record containing source, locator, snapshot/version, claim, confidence, freshness, and provenance.

Facts must be directly supported. Inferences must identify their supporting facts. Unknowns remain unknown. Recommendations are not evidence.

## 3. Proof Bundle

A completed change should produce a compact proof record containing:

- contract/requirement IDs;
- protected behavior;
- changed files/symbols;
- diff identity;
- verification commands/results;
- relevant static, compatibility, security, and runtime evidence;
- review result;
- outcome status and outcome evidence where available;
- unresolved risks.

Missing evidence must be reported, not replaced with model confidence.

## 4. One-shot task contract

For non-trivial requests, consolidate consequential ambiguity into one clarification package:

`Goal | Non-goals | Requirements | Protected behavior | Acceptance | Risks | Questions`

Ask only questions whose answers materially change correctness, safety, scope, architecture, or verification.

## 5. Repository Engineering Profile

On first meaningful interaction, infer a compact profile from repository instructions and observed code. Classify each profile fact as:

`explicit | observed | inferred | unknown`

Capture build/test commands, language/framework, source layout, dependency conventions, error handling, logging, telemetry, test patterns, API/data contracts, deployment, architecture boundaries, and high-risk areas.

Cache stable facts and invalidate only affected facts after repository changes.

## 6. Deterministic risk model

Score the following dimensions independently from 0 to 3:

- scope
- blast_radius
- reversibility
- data_risk
- security_risk
- production_impact
- contract_risk
- uncertainty

Use the maximum dimension plus the aggregate to select controls. Risk scores are decision aids, not permission to bypass repository or organization policy.

Suggested controls:

- low: normal focused verification;
- medium: explicit contract and regression verification;
- high: grilling, impact analysis, broader verification, and fresh review where practical;
- critical: explicit approval and isolated/sandboxed execution for risky side effects.

## 7. Friction and thrash

Track clarification rounds, user corrections, repeated equivalent tool calls, repeated failed tests, resets, and abandoned plans.

A retry is valid only when it changes evidence, hypothesis, tool strategy, or scope. Repeated non-progress must trigger a strategy change or explicit escalation.

The primary productivity signal is quality-adjusted time-to-proven-change.

## P0 acceptance criteria

A P0 implementation is ready only when:

1. the state schema validates representative state;
2. material decisions can reference evidence;
3. proof output can identify what was changed and what proved it;
4. consequential ambiguity is consolidated instead of serialized into many questions;
5. repository profile facts have provenance/status;
6. risk changes verification and approval behavior;
7. non-progress is measurable and does not silently loop;
8. all behavior degrades safely when optional providers are absent;
9. deterministic evals cover the above invariants;
10. documentation explains the behavior without requiring knowledge of internal implementation;
11. outcome can be captured separately from verification so learning can distinguish test success from accepted/operational success.
