# Dependency and Framework Policy

This repository is treated as a fresh Python 3.11+ harness because no existing application logging, telemetry, exception framework, package manager, or external test framework was found.

## Adopted baseline

The default implementation uses only the Python standard library:

- `logging` for application logging
- explicit exception types plus a top-level crash boundary for exception handling
- local JSONL telemetry for run events
- `unittest` for unit testing
- `tomllib`, `argparse`, `subprocess`, `pathlib`, and other standard modules for infrastructure

No new third-party dependency is required for the baseline harness.

## Optional third-party libraries

These are documented but are NOT incorporated by default:

| Library | Purpose | Status | Why not included by default |
|---|---|---|---|
| OpenTelemetry | Export traces/metrics/logs to external observability systems | Opt-in | Requires an external backend and deployment decision |
| pytest | Richer Python test discovery and fixtures | Opt-in | The repository currently has no pytest convention; `unittest` is sufficient |
| structlog | Structured application logging | Opt-in | Standard `logging` is sufficient for the current harness |
| tenacity | Advanced retry policies | Opt-in | Harness retries are small, explicit, and phase-aware |

Before introducing any optional library, create or update an explicit dependency decision in the repository and document the reason, scope, version policy, and operational impact.

## Existing-project rule

For a non-fresh repository, agents MUST first detect and reuse the existing:

- exception hierarchy and error-handling conventions
- logging framework, sinks, formats, correlation identifiers, and log levels
- telemetry/tracing/metrics implementation
- unit/integration test framework, fixtures, helpers, and naming conventions
- dependency/package management system

Do not introduce a competing framework merely because it is newer or more capable.

## Fresh-repository rule

When the repository has no established convention, use the simplest broadly supported standard-library implementation first. Add a third-party framework only when the task requires capabilities that the baseline cannot reasonably provide.
