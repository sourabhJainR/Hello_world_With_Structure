# Knowledge Fabric Policy

## Purpose

The harness uses a layered code-intelligence fabric instead of treating the repository as raw text.

## Retrieval order

1. Repository instructions and explicit task constraints.
2. Fresh structural index when available: AST, symbol, import, call and dependency relationships.
3. Graph traversal for impact, ownership, callers/callees and cross-module relationships.
4. Exact lexical retrieval for identifiers, errors, APIs and configuration keys.
5. Semantic retrieval for conceptual matches when a local semantic provider is configured.
6. Targeted source reads for final evidence.
7. Verification output is authoritative over retrieved suggestions.

## Graphify compatibility

Graphify is an optional local knowledge-graph provider. The harness may consume its `graph.json`/`graphify-out` artifacts or invoke its CLI when explicitly enabled. Graphify remains the owner of graph construction and MCP lifecycle.

## code-memory compatibility

`codebase-memory-mcp` is an optional structural intelligence provider. The harness may query its CLI or consume its local graph artifacts when explicitly enabled. MCP transport, installation, upgrades and agent configuration remain owned by the user's MCP client/tooling.

## Hybrid retrieval

The architecture supports a BM25/lexical + dense/semantic + graph ranking model. No embedding or reranking dependency is required by default. If a semantic reranker is introduced, it must be an opt-in provider and documented in `DEPENDENCIES.md`.

## AST and language neutrality

Prefer an existing repository AST/indexer or an installed Graphify/code-memory index. Do not add a parser dependency merely to inspect a single task. A language-specific parser may be used only when the repository already uses it or the task justifies it.

## Provenance

Every external knowledge result should retain source, query, timestamp/session, and whether the relationship was extracted or inferred when that metadata is available. Inferred graph edges must never be represented as confirmed source facts.

## Freshness

Prefer indexes matching the current git commit. If the index is stale or its coverage is unknown, mark the evidence stale and fall back to targeted source reads.

## Context budgeting

Structural queries should replace broad file enumeration where possible. Return signatures, paths, symbols, relationships, and relevant snippets before full files. Verification evidence must never be removed solely to save tokens.

## Failure behavior

External knowledge providers are advisory. A missing, stale, malformed, or failed provider must not prevent normal repository inspection unless the task explicitly requires that provider.

## Security

The harness never installs, upgrades, or modifies Graphify/code-memory configuration automatically. External commands are executed without a shell, within configured timeouts, and only when the provider is enabled.
