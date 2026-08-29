# Operating Model

## Lifecycle

`Understand -> Profile -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if needed -> Learn -> Stop`

The default is one adaptive run. Recursive looping is disabled unless the user explicitly requests a loop.

## Routing

Classify intent, scope, risk, uncertainty, reversibility, and change surface. Use the smallest safe workflow. Research, POC, Debug, Grill, Review, Validate, and Learn are capabilities selected only when useful.

## Evidence order

1. Repository and organization instructions.
2. Acceptance criteria and task source.
3. AST/symbol/index evidence.
4. Graph relationships and impact paths.
5. Exact lexical evidence.
6. Semantic retrieval.
7. Targeted source reads.
8. Tests/build/CI/runtime output and final diff.

## Implementation

Inspect siblings and existing patterns before creating files or abstractions. Preserve local naming, package/module boundaries, exception handling, logging, telemetry, dependency injection, configuration, retry, client, and test patterns. If no local pattern exists, use a mature compatible ecosystem convention and disclose new dependencies.

## Architecture and operational quality

For both new systems and enhancements, review the resulting design for weak boundaries, poor separation of concerns, fragile data models, operational gaps, and inadequate observability. Apply the repository's established architecture first; do not create a parallel framework.

Check relevant concerns before completion:

1. Clear responsibility and dependency boundaries.
2. Cohesive components with explicit side effects and minimal coupling.
3. Data invariants, lifecycle, compatibility, concurrency, and failure semantics.
4. Production behavior: errors, timeouts, retries, cancellation, idempotency, cleanup, configuration, migrations, and rollback when relevant.
5. Diagnostics: repository-native structured logs, actionable metrics, tracing/correlation, and health signals for operationally meaningful changes.
6. Security and privacy: no secrets or sensitive payloads in logs/telemetry.

A passing test suite is necessary but does not prove architectural or operational quality. If a broader redesign is required but out of scope, keep the local change safe and explicitly report the remaining limitation.

## Verification

A model assertion is never sufficient. Match verification to acceptance criteria and risk. Every retry must add evidence or materially change the approach.

## Safety

Use isolated worktrees for high-risk or experimental mutation. Never silently install tools, change permissions, access production, merge changes, or execute unapproved external actions.

## Completion

Return the result, evidence, changed files, review status, extensions used, assumptions, risks, and incomplete checks.
