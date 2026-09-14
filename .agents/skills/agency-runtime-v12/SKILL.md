# Agency Runtime v12 — graph-aware retrieval

Use this skill when a coding task needs repository context before an agent edits code.

## Contract

`workspace_root` enables deterministic indexing. Retrieval starts with a small lexical/path/symbol seed set, then expands up to `context_graph_hops` (0–2) through typed graph edges:

- `imports`: direct module/file dependency
- `calls`: symbol call relationship; reverse traversal supplies callers and forward traversal supplies callees
- `implements`: inheritance/interface relationship
- `tests`: conservative test-to-source association; this is context, not proof of line coverage
- `configures`: configuration-to-source association

Every edge has a confidence and reason. The context carries `graph_trace`, including seed paths, expanded paths, selected edges and explicit stop reasons.

## Token discipline

The graph is used for navigation, not dumped into the model. Only bounded source windows become `ContextChunk`s. `context_token_budget` remains the hard context ceiling and `context_max_files` limits the final file set. Files excluded by budget are reported in `unknowns`.

## Orchestration flow

`CodingTask -> adaptive recommendation -> graph-aware context -> TaskProfile.context -> specialist selection -> execution -> evidence/verification -> artifact regression -> release gate -> benchmark observation`.

The host remains responsible for model calls, tools, permissions, concurrency and side effects. The portable runtime only supplies deterministic evidence and orchestration state.

## Unknown policy

Do not silently infer missing code. Surface no seed match, unreadable files, budget omissions and graph stop conditions as explicit unknowns and record them in provenance. A graph edge is evidence of a relationship, not proof of runtime execution.

## Evaluation

v11 deterministic retrieval/answer metrics remain compatible. Graph expansion improves the evidence set but does not bypass faithfulness, regression, release or provenance gates.
