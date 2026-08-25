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

## Verification

A model assertion is never sufficient. Match verification to acceptance criteria and risk. Every retry must add evidence or materially change the approach.

## Safety

Use isolated worktrees for high-risk or experimental mutation. Never silently install tools, change permissions, access production, merge changes, or execute unapproved external actions.

## Completion

Return the result, evidence, changed files, review status, extensions used, assumptions, risks, and incomplete checks.
