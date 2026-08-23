# Dependency and Framework Policy

This repository is treated as a fresh Python 3.11+ harness because no existing application logging, telemetry, exception framework, package manager, or external test framework was found.

## Adopted baseline

The default implementation uses only the Python standard library:

- `logging` for application logging
- explicit exception types plus a top-level crash boundary for exception handling
- local JSONL telemetry for run events
- `unittest` for unit testing
- `tomllib`, `argparse`, `subprocess`, `pathlib`, and other standard modules for infrastructure

No new third-party Python dependency is required for the baseline harness.

## Optional third-party libraries

These are documented but are NOT incorporated by default:

| Library | Purpose | Status | Why not included by default |
|---|---|---|---|
| OpenTelemetry | Export traces/metrics/logs to external observability systems | Opt-in | Requires an external backend and deployment decision |
| pytest | Richer Python test discovery and fixtures | Opt-in | The repository currently has no pytest convention; `unittest` is sufficient |
| structlog | Structured application logging | Opt-in | Standard `logging` is sufficient for the current harness |
| tenacity | Advanced retry policies | Opt-in | Harness retries are small, explicit, and phase-aware |

## Optional external extensions

These are integrations, not Python runtime dependencies of this repository. They are never installed, upgraded, enabled, disabled, or mutated automatically by the harness.

| Extension | Purpose | Status | License/source note |
|---|---|---|---|
| Graphify (`graphifyy`) | Local AST/knowledge graph, graph traversal, code/document relationships | Opt-in | Official Graphify source currently documents Apache-2.0; verify the exact release before adoption |
| codebase-memory-mcp | Local persistent code graph, AST/LSP-aware structural search, impact analysis | Opt-in | Official repository currently documents MIT; verify the exact release before adoption |
| Superpowers | Process skills such as brainstorming, TDD, systematic debugging, planning, execution | Opt-in | Official repository documents MIT |
| Ponytail | YAGNI/minimal-change discipline | Opt-in | Official repository documents MIT |
| Caveman | Output/context compression and token efficiency | Opt-in | Official repository documents MIT |

See `.ai-harness/extension_registry.toml` for capability mappings and detection markers.

Before adopting any optional library or external tool, document purpose, scope, version/release policy, security and operational impact, ownership, alternatives considered, and rollback/removal path.

## Existing-project rule

For a non-fresh repository, agents MUST first detect and reuse the existing:

- exception hierarchy and error-handling conventions
- logging framework, sinks, formats, correlation identifiers, and log levels
- telemetry/tracing/metrics implementation
- unit/integration test framework, fixtures, helpers, and naming conventions
- dependency/package management system
- AST/index/search/graph tooling already present
- agent skills and MCP integrations already configured by the team

Do not introduce a competing framework merely because it is newer or more capable.

## Fresh-repository rule

When the repository has no established convention, use the simplest broadly supported standard-library implementation first. Add a third-party framework only when the task requires capabilities that the baseline cannot reasonably provide.
