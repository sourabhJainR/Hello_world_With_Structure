# AER 22.0.0

## Collective Learning Runtime

AER 22.0.0 marks the move from execution-only orchestration to an execution and collective-learning runtime.

### Highlights

- Bounded context engineering keeps execution context small and task-focused.
- Private working memory remains session-scoped and is never automatically promoted.
- Shared task memory carries only the context needed by dependent agents.
- The Learning Steward captures both successful and failed execution experience.
- Post-run Dreaming promotes repeated, independently observed patterns and anti-patterns.
- Conflicting evidence remains unresolved instead of contaminating durable guidance.
- Durable learning is versioned, evidence-backed, auditable, and concurrency-safe.
- Repository truth remains authoritative; durable learning is guidance, not a replacement for source files or verification.
- The portable distribution is now a single canonical `aer-portable.zip` containing the AER launcher, runtime, skills, plugin metadata, and integrity manifest.
- CI publishes only that canonical distribution instead of separate `aer-portable.zip`, `aer_cli.py`, and extracted copies.

## Distribution contract

The canonical AER distribution is:

```text
aer-portable.zip
├── aer-bundle.json
├── aer_cli.py
└── payload/
    ├── .ai-harness/
    ├── .claude-plugin/
    ├── .claude/
    ├── portable/
    └── skills/
```

`aer_cli.py` is part of the bundle and is integrity-covered by `aer-bundle.json`. There is no separate CLI artifact to download or keep in sync.

## Versioning

- Plugin version: `22.0.0`
- Bundle format remains compatible with the existing portable installer contract.
- The bundle manifest records the semantic version and exact source commit for reproducibility.

## Verification

The release workflow validates the full test suite, bundle integrity, plugin payload, version consistency, artifact policy, and the single-file distribution before publishing the canonical portable artifact.
