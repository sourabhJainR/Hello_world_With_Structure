# v12 graph-aware retrieval

v12 extends the v11 evidence-first context layer without increasing the default model context size.

## Retrieval path

1. Index source files, symbols, imports, calls and inheritance/interface declarations.
2. Rank a small seed set from the task/query.
3. Expand at most two graph hops from the strongest seeds.
4. Prefer callers/callees, then interface/implementation relationships, tests and configuration.
5. Read only bounded line windows from the selected files.
6. Enforce the token budget before a chunk enters model context.
7. Record graph edges, confidence, reasons and stop conditions in `GraphTrace`.
8. Pass the immutable `CodebaseContext` through `TaskProfile.context` into the coding worker.
9. Continue through specialist planning, evidence, verification, regression, release and benchmark stages without bypassing any gate.

## Edge semantics

`imports` means the parser resolved a local import/module candidate. `calls` means a source call name was matched to a symbol; reverse traversal is exposed as caller context and forward traversal as callee context. `implements` connects inheritance/interface declarations. `tests` is a conservative test association and is not a coverage claim. `configures` identifies configuration files that reference a source target.

Confidence is part of the evidence. Ambiguous symbol matches are lower confidence than same-file matches. No model call is required to build the graph.

## Unknowns

The system reports no seed match, unreadable files, budget omissions, missing graph successors and exhausted hop budgets. These are retained in provenance so a worker cannot mistake an incomplete context window for a complete repository understanding.

## Why this is useful

This follows the strongest ideas found in Repowise: graph-first navigation, explicit relationship semantics, confidence-bearing evidence, bounded graph expansion, separate test/config context and proactive context discipline. It intentionally does not copy Repowise's tree-sitter, SQLite, vector/RRF or git-history stack into the portable runtime. Those would add significant dependencies and operational cost; they are candidates for a future host adapter rather than hidden dependencies in the core.
