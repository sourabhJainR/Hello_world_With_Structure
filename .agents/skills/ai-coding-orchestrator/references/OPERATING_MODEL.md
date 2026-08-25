# Operating Model

## Lifecycle

`Understand -> Profile -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if needed -> Learn -> Stop`

One adaptive run is the default. Recursive looping is disabled unless the user explicitly requests a loop.

## Routing

Classify intent, scope, risk, uncertainty, reversibility, and change surface. Use the smallest safe workflow. Research, POC, Debug, Grill, Review, Validate, and Learn are selected only when useful.

## Evidence

Prefer repository/team instructions and acceptance criteria, then AST/symbol evidence, graph relationships, exact search, semantic retrieval, targeted source reads, and tests/build/CI/runtime evidence.

## Implementation

Inspect siblings before creating files or abstractions. Preserve local naming, placement, module boundaries, exception handling, logging, telemetry, DI, configuration, retries, clients, dependencies, and tests. If no local pattern exists, use a mature compatible ecosystem convention and disclose dependencies.

## Verification and safety

A model assertion is not evidence. Match verification to risk and acceptance criteria. Use isolated worktrees for high-risk or experimental mutation. Never silently install tools, change permissions, access production, merge changes, or bypass approval boundaries.
