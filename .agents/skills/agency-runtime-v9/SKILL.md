---
name: agency-runtime-v9
description: Conflict-aware multi-specialist execution planning for Agency Runtime, with deterministic scheduling, explicit resource ownership, serialized mutations, and parallel read-only work.
---

# Agency Runtime v9

## Contract
The planner decides **who may work when**; it does not execute commands or mutate files.

Every specialist work unit must declare:
`ROLE | MUTATION_MODE | READ_PATHS | WRITE_PATHS | DEPENDENCIES | PRIORITY`.

## Scheduling rules

1. Read-only specialists with no dependency or resource conflict may share a wave.
2. Any write/write overlap is a conflict and must be serialized.
3. A write/read overlap is a conflict and must be serialized.
4. Independent mutations are still serialized so mutation order remains explicit and auditable.
5. Dependencies create ordering edges; a dependent specialist cannot enter an earlier wave.
6. Unknown dependencies block the plan instead of being silently ignored.
7. Read-only work must never declare write paths.
8. Mutating work must explicitly declare write paths.

## Determinism
Plans are stable for the same work specification. Ordering uses priority, role, specialist name, dependencies, and resource conflicts. Every plan exposes a digest suitable for provenance and regression history.

## Provenance
Record the execution-plan digest alongside specialist selection, evidence, verification, regression, and release events. Do not put secrets or raw sensitive payloads into scheduling metadata.

## Host boundary
The AI coding orchestrator remains responsible for sandboxing, credentials, permissions, command execution, external side effects, and the final mutation mechanism. The planner only supplies an auditable execution schedule.

## Failure handling
A missing dependency or invalid resource declaration is a planning failure. A conflict is not itself a failure; it is a scheduling fact that must result in serialization. Never report parallel execution where the plan serialized the work.
