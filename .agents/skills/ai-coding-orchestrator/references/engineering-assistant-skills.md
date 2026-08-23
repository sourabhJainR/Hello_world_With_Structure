# Engineering Assistant Skill Modules

These modules are capabilities selected by the adaptive router. They are not separate autonomous agents unless the provider supports isolated delegation.

## Contextual Bug Fixer

Inputs: stack trace, error/event payload, affected service, deployment version, Git commit.

Process:
1. Resolve the exact commit/worktree.
2. Map the error to symbols/files using structural search or graph evidence.
3. Trace callers, callees, data flow, and configuration dependencies.
4. Reproduce or create the smallest deterministic failing test.
5. Implement the smallest compatible fix.
6. Run regression and affected-area verification.
7. Explain the root cause and cite evidence.

Never infer a source line from a different commit without marking the mapping uncertain.

## Impact Analyzer

Inputs: diff, pull request, migration, API/schema/config change.

Process:
1. Map changed symbols and files.
2. Traverse downstream dependencies and public contracts.
3. Identify API, schema, data, tenancy, compatibility, deployment, and operational impact.
4. Identify test gaps and affected validation suites.
5. Produce a severity-ranked impact report with evidence paths.

Prefer recall for impact discovery; unresolved candidates are reported rather than silently discarded.

## Automated Boilerplate and Migration

Before generating boilerplate:

1. Find the nearest mature implementation.
2. Reuse its naming, placement, dependency injection, validation, error handling, logging, telemetry, authorization, testing, and configuration patterns.
3. For migrations, inspect the current schema and migration history first.
4. Generate migration + rollback/compatibility handling + tests + API/OpenAPI documentation where applicable.
5. Validate generated artifacts using repository-native tooling.

Generated migrations are never executed against production by the assistant.

## Onboarding and Code Explorer

Answer questions using a layered evidence model:

1. Repository instructions.
2. Structural graph/AST evidence.
3. Exact source and documentation.
4. Version history when the question asks why or when.

Explain the path taken through the architecture and distinguish extracted facts, inferred relationships, and model interpretation.

## Shared contract

Every module must provide:

- task interpretation;
- evidence sources;
- confidence/uncertainty;
- affected scope;
- recommended action;
- verification plan;
- remaining risks.

The modules use the same knowledge fabric, context budget, worktree policy, review policy, and dependency policy as the core orchestrator.
