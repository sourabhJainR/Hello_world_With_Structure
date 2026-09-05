# Requirement-level engineering traceability

The engineering loop now persists a machine-readable trace from the originating work item through acceptance, implementation, verification, learning and replay:

```text
Jira / Requirement
        ↓
Acceptance Criterion
        ↓
Design
        ↓
Code change
        ↓
Test
        ↓
Evidence
        ↓
Regression knowledge
        ↓
Replay result
        ↓
WorkReport
```

## Contract

`.ai-harness/runtime/requirement_traceability.py` is the canonical normalizer and persistence boundary. It produces:

- `.ai-harness/reports/traceability/<work-id>-requirements.json`
- requirement and acceptance-criterion IDs
- design/code/test/evidence pointers
- linked regression IDs
- replay IDs and replay status
- coverage counts and residual gaps

The existing WorkReport traceability file continues to provide the broader learning context in `.ai-harness/reports/traceability/<work-id>.json`.

## Evidence rules

- Requirement text is accepted only from explicit Jira/requirement input or an explicit requirement field.
- Acceptance criteria are never invented from a task description.
- Missing design, code, test, evidence or replay information is represented as a residual gap.
- Historical RegressionMemory is advisory planning evidence.
- Regression replay, shadow, canary, promotion and rollback remain authoritative gates.
- Traceability never grants credentials, permissions, merge authority or security exemptions.

## Coverage semantics

`covered` means the requirement has an explicit acceptance criterion plus design, code, test and evidence pointers, and any supplied replay results passed.

`partially-covered` means some evidence exists but at least one required link is missing or replay failed.

`uncovered` means no usable implementation evidence has been recorded.

## Regression and replay

Regression IDs are attached to each requirement trace when historical or newly learned regression knowledge is available. Replay results may be supplied by the run manifest using `replay_results` and are persisted without changing their authority or inventing results.

## Determinism

Generated requirement IDs are SHA-256-derived from normalized requirement text when an upstream ID is absent. This makes the same requirement stable across runs while preserving upstream Jira IDs when available.
