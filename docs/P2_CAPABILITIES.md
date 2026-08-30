# P2 Capabilities

P2 adds provider-neutral contracts that remain dependency-free and safe to run in core CI.

## Model routing

`route_model` selects among declared model capabilities using task complexity, quality, latency and cost constraints. Incompatible models are rejected instead of being selected and failing later.

## Durable project memory

`memory_record` stores a compact, provenance-bearing observation with confidence, tags and optional expiry. `select_memory` only returns active records for the requested topic and applies a deterministic limit.

Memory is advisory context. It must not silently modify policy, permissions or security behavior.

## Change-risk prediction

`predict_change_risk` estimates a deterministic risk level from changed-file count, dependency fan-out, test coverage, API/schema changes and historical defects. Higher risk adds verification and approval controls; it never bypasses verification.

## Evaluation promotion gate

`compare_eval_baseline` compares a candidate against a stable baseline. Required metric regressions block promotion even when another metric improves.

## Rollback and safety

P2 remains additive. Existing P0/P1 runtime contracts are unchanged. P2 selection and memory are advisory unless a future policy explicitly promotes them. Any promoted policy must retain a stable baseline, deterministic tests, negative cases, degraded behavior, context-budget evidence, security review and a rollback path.
