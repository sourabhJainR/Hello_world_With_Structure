# Repository Construct Traceability

## Purpose

The coding workflow must ground plans, research, POCs, HLDs, LLDs, implementation notes, maintenance decisions, and verification evidence in the actual target repository.

This is a repository-engineering rule. It is not a generic documentation convention.

## Mandatory reference rule

Whenever a task materially depends on an existing repository element, reference the exact construct when one is available:

- file
- namespace/module/package
- class
- record/struct
- interface
- enum
- function/method
- property/field
- API/endpoint
- event/message/queue
- JSON/YAML/TOML/XML key or schema element
- SQL query
- stored procedure
- view
- table
- function
- migration
- index
- test
- build target
- external command

Preferred form:

`[construct-id] kind path:line::name`

Example:

`[rc-0123456789ab] function src/order/OrderService.cs:84::CreateOrderAsync`

The construct ID is generated from the indexed repository path, construct kind, name, and source line. The path/symbol remains visible so the artifact is useful without tooling.

## Evidence rules

1. Inspect the repository before making architectural or implementation claims.
2. Resolve references against the current construct index.
3. Do not invent classes, methods, interfaces, database objects, schemas, configuration keys, or tests.
4. If a referenced construct is not found, write `UNRESOLVED CONSTRUCT` and explain what evidence is missing.
5. HLD components must map to one or more actual repository files/modules.
6. LLD elements must map to actual symbols or explicitly identify new symbols as `NEW CONSTRUCT`.
7. Implementation plans must identify expected files and constructs before editing when the constructs already exist.
8. Verification must map tests/commands/results back to the constructs they validate.
9. Research and POC results must identify the repository boundary they examined or changed.
10. Database claims must name the actual stored procedure/view/table/query when such objects exist. Never replace an absent database path with a generic database description.

## Construct lifecycle

Use these labels when appropriate:

- `EXISTING CONSTRUCT` — resolved in the current repository index.
- `NEW CONSTRUCT` — intentionally proposed/created by the task and therefore not expected to exist before implementation.
- `UNRESOLVED CONSTRUCT` — referenced but not found; this is an evidence gap, not permission to guess.
- `DELETED CONSTRUCT` — previously known but removed by the current change.

## Artifact traceability

The workflow should maintain this chain:

`task -> research evidence -> plan -> HLD -> LLD -> implementation -> tests/validation -> result`

Each transition should preserve concrete repository references where applicable.

The construct index is supporting evidence, not a replacement for reading the relevant source. For important changes, the LLM must inspect the referenced source and its callers/dependencies rather than relying on a signature-only index entry.

## Stability

Line numbers are supporting location evidence. The semantic path and symbol are the primary human-readable reference. Construct IDs are deterministic for the indexed path/kind/name/line tuple.

The index is dependency-free and intentionally supports multiple languages and repository data formats. Language-specific parsers can be added later without changing the artifact contract.

## Scope separation

This policy belongs only to `Hello_world_With_Structure`. It has no dependency or relationship with any other repository or project.