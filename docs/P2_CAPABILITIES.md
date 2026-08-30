# P2 Capabilities

P2 provides provider-neutral, dependency-free advisory intelligence around model choice, bounded project memory, change risk, and evaluation promotion.

## Model routing

`route_model` selects among declared model capabilities using task complexity, quality, latency, and cost constraints. Hard latency/cost/capability constraints are filters, not score penalties. Selection is deterministic and stable under ties.

## Durable project memory

`memory_record` creates compact observations with provenance, confidence, tags, deterministic IDs, and optional expiry. Records are bounded to 4,096 characters and reject common secret-like assignments. `select_memory` returns only valid, active records for the requested topic, in deterministic order, with a maximum of 100 records.

`save_memory` persists validated records atomically without requiring a database. External memory systems such as code-mem may implement a richer provider behind the same conceptual boundary.

Memory is advisory context. It must not silently modify policy, permissions, security behavior, or repository instructions.

## Change-risk prediction

`predict_change_risk` estimates a deterministic risk level from changed-file count, dependency fan-out, coverage, API/schema changes, and historical defects. Invalid numeric inputs fail closed. Higher risk adds verification and approval controls; it never bypasses verification.

## Evaluation promotion gate

`compare_eval_baseline` compares baseline and candidate metrics. Required metrics must exist on both sides. Metric direction can be explicit as `higher` or `lower`, so measures such as accuracy and latency are evaluated correctly. Any required regression or missing required metric blocks promotion.

## P2 pipeline

`p2_pipeline.py` connects routing, risk, and bounded memory retrieval to the P0 evidence/decision model. P2 results become traceable evidence rather than hidden heuristics.

## Safety and compatibility

P2 is advisory and additive. Existing P0/P1 contracts remain stable. Optional providers are not required. Promoting P2 behavior into executable policy requires a stable baseline, deterministic positive/negative tests, degraded-mode behavior, context-budget evidence, security/permission review, and rollback capability.
