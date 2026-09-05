# WorkReport -> RegressionMemory Traceability

The engineering work loop now connects durable work evidence to future regression planning.

## Flow

`Task -> historical RegressionMemory -> execution -> verification -> WorkReport -> verified findings -> RegressionMemory -> future planning/replay`

## Rules

- WorkReport is an evidence record, not an approval mechanism.
- Only explicit findings/regressions are ingested; the bridge never invents root cause, reproduction, fixes, tests, or evidence.
- A finding is eligible for active regression knowledge only when the work completed, verification passed, confidence is sufficient, and both evidence and test pointers are present.
- Unverified findings remain pending and are retained as evidence.
- Historical regression IDs are persisted into `reports/traceability/<work-id>.json` and exposed through `reports/planning-context.json`.
- Regression selection remains deterministic and includes historical knowledge provenance in its fingerprint.
- Replay, shadow, canary, promotion, rollback, security, permissions, and human approval gates remain authoritative.

## Artifacts

- `.ai-harness/reports/<work-id>.html` — human-readable dossier.
- `.ai-harness/reports/traceability/<work-id>.json` — machine-readable lineage.
- `.ai-harness/reports/planning-context.json` — compact historical planning inputs.
- `.ai-harness/learning/regression-memory.db` — durable verified/pending regression knowledge.

## Future work

A later enhancement can map requirement IDs and acceptance criteria to individual regression IDs and replay case IDs. Until those identifiers are explicitly available, the system records the strongest evidence-backed linkage it can prove and marks the rest as unknown rather than guessing.
