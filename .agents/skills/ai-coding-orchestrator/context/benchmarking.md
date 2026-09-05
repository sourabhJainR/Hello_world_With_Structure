# Engineering Benchmark Pack

Load only when running or designing behavioral conformance.

Ground truth is independent of provider claims:
`fixture -> baseline fingerprint -> provider execution -> post fingerprint -> task oracle -> mutation/hidden/invariant checks -> recovery/regression analysis`.

Required evidence classes:
- baseline/post repository and test fingerprints
- task-specific executable acceptance oracles
- independent mutation tests proving the oracle can detect defects
- hidden acceptance cases not included in provider prompts
- AST/static invariants for structural requirements and security constraints
- deterministic failure injection with explicit injection markers
- exact ordered failure -> diagnosis -> retry -> success evidence
- Context Broker telemetry captured independently when available
- behavioral score separated from oracle coverage/observability

Never convert missing telemetry into a behavioral pass. Report `observability_score` separately and expose uncovered dimensions.

A benchmark pass requires the task oracle, provider exit status and contract completeness. Provider self-report is advisory only.
