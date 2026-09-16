# Repository Model Consolidation

AER has one canonical repository model: `portable.agency_codebase_context.CodebaseIndex`.

`portable.repository_intelligence.RepositoryIntelligence` and
`portable.repo_intelligence.RepositoryMap` are task-facing compatibility facades.
They may add retrieval, packing, security filtering, token budgeting and CLI
presentation, but they must consume the canonical index rather than crawl the
repository independently.

## Canonical responsibilities

`CodebaseIndex` owns:

- deterministic repository file inventory for supported text/config sources;
- ignore-directory and ignore-file inclusion rules;
- file identity and snapshot digest;
- symbol, import, call, implementation and test relationships;
- graph-neighbor queries used by context retrieval.

The index includes hidden repository directories unless explicitly ignored.
This matters for repositories whose engineering/runtime contracts live under
`.ai-harness`, `.github`, `.agents`, `.claude`, or similar hidden paths.

## Facade responsibilities

`RepositoryIntelligence` owns task-facing behavior only:

- ranking and answer formatting;
- bounded packing from `CodebaseIndex.files`;
- secret filtering before model context emission;
- token accounting and optional structural compression;
- git change awareness;
- CLI/compatibility presentation.

Its `repository_model` property explicitly exposes the underlying canonical
`CodebaseIndex` for integrations that need the shared model.

## Consistency invariant

All repository-context operations in the same facade instance use the same
index and snapshot. Refreshing the repository model replaces that one index; it
does not maintain parallel indexes for search, packing, impact analysis or test
selection.

The consolidation deliberately keeps public classes and CLI modes stable. The
architectural change is ownership and reuse, not an unnecessary API rewrite.
