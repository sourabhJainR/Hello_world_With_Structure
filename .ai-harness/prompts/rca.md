# RCA / regression analysis

This phase is analysis-only.

Do not edit source, tests, configuration, documentation, dependencies, or infrastructure. Do not create or apply a patch. Do not commit or push.

Investigate the reported failure deeply within the current task boundary.

Required analysis:

1. Establish the failure timeline and the first observable deviation.
2. Identify the actual runtime entry point and trace the relevant call/data flow.
3. Inspect branch conditions, configuration/feature gates, fallbacks, persistence, integrations, concurrency, and error paths that can affect the failure.
4. Compare working and failing data shapes where the behavior may be shape-dependent.
5. Use repository source, tests, logs, history, runtime traces, and optional graph/memory evidence as available.
6. Record exact evidence for each material finding.
7. Rank root-cause hypotheses with evidence for and against each.
8. Separate confirmed facts, inferences, unknowns, contradictions, and recommendations.
9. Identify the smallest missing verification needed to move an unproven hypothesis toward proof.

Return:

`RCA status | Timeline | Entry point | Flow | Data-shape differences | Evidence | Hypotheses | Contradictions | Unknowns | Root cause | Follow-up`

A recommendation may describe what should be investigated or changed later, but this phase must not implement it.