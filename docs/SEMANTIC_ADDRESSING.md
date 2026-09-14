# Semantic addressing

`portable.semantic_addressing` adds stable semantic references without creating a second index or retrieval engine.

## Ownership

- `portable.agency_codebase_context.CodebaseIndex` owns parsing, indexing, graph edges and repository snapshots.
- `portable.agency_codebase_context.retrieve()` owns ranked context retrieval and graph expansion.
- `portable.semantic_addressing.SymbolLocator` only resolves symbols and exposes graph relationships from that canonical index.
- `portable.repository_intelligence.RepositoryIntelligence` remains the single repository context entry point for retrieval and bounded packing.

## Address format

A symbol is addressed as:

```text
relative/path.py::SymbolName
```

The resolved `SymbolAddress` also carries the index snapshot digest. Agents should treat the digest as the validity boundary: after repository mutation, call `RepositoryIntelligence.refresh()` and resolve the reference again rather than assuming the old location is current.

## Why this is useful

This follows the useful Serena pattern of semantic symbol addressing while keeping the existing graph-aware implementation as the owner. It supports research, investigation, code review, bug fixing and test generation without introducing another retrieval store.

Ambiguous symbols are returned as explicit path-qualified candidates instead of silently choosing one.
