# Current Architecture

This document describes the current AER 23.x architecture. Historical version notes remain provenance records and do not redefine runtime ownership.

## Engineering spine

```text
User task
  -> intent / contract
  -> CodebaseIndex repository facts
  -> canonical evidence ledger
  -> TaskPlan
  -> ExecutionEnvelope
  -> StateGraph
  -> verification / review
  -> regression / release
  -> outcome
  -> advisory learning
```

## Canonical authorities

| Concern | Authority |
| --- | --- |
| Repository truth | `portable.agency_codebase_context.CodebaseIndex` |
| Evidence truth | `state/engineering-state.schema.json:evidence` |
| Planning | `portable.task_planner.TaskPlan` |
| Cross-phase contract | `portable.execution_contract.ExecutionEnvelope` |
| Execution | `portable.agency_state_graph.StateGraph` |
| Capabilities | `portable.agent_capabilities.CapabilityFabric` |
| Verification | `state/engineering-state.schema.json:verification` |
| Release gates | `docs/REGRESSION_CANARY.md` |
| Learning | `portable.agency_adaptive_planning` |
| Architecture views | `skills/engineering/interactive-documentation` |

Compatibility surfaces are adapters, strategies, views, or historical records and are catalogued in `architecture/compatibility.yaml`.

## Operating rules

No second repository graph, evidence store, workflow engine, capability catalog, or memory authority is introduced. Learning is advisory. Evidence carries snapshot identity and must be refreshed when repository truth changes. Execution state is serializable and checkpoint digests are verified. Release remains downstream of verification.

The portable layer remains provider-neutral and dependency-light; provider, host, skills, and reporting integrations remain outside canonical execution semantics.
