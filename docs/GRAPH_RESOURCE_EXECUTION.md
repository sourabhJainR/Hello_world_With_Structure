# Graph resource-aware execution

`GraphAgentTeam` now treats `LocalOffloadBroker` as an execution lane beneath the existing graph.

```text
task
  -> TaskPlan dependencies
  -> StateGraph ready set
  -> resource decision
       |-- local deterministic work
       |-- existing agent/cloud lane
  -> bounded parallel execution
  -> compact evidence in SharedTaskMemory
  -> verifier/reviewer
  -> synthesizer
  -> existing learning steward
```

## Ownership

This layer does not create a second planner, scheduler, graph, memory store, verifier, or learning system.

- `TaskPlan` remains the dependency-planning owner.
- `StateGraph` remains the execution and checkpoint owner.
- `GraphAgentTeam` remains the agent-team owner.
- `CapabilityFabric` remains the capability/policy owner.
- `LocalOffloadBroker` remains the bounded local execution resource.
- Verification and review remain authoritative.
- `LearningSteward` remains the durable learning owner.

## Automatic resource choice

An agent is eligible for the local lane only when it is read-only and declares deterministic local work. Mutating agents stay on the existing agent lane.

The route can provide a verification command:

    verification_command=("python", "-m", "pytest", "-q")

If omitted, implementation/debug/poc routes default the verifier to `python -m pytest -q`.

Local output is bounded by the existing broker budgets and is handed to the agent as evidence. The output is never treated as instructions.

## Failure behavior

A local failure does not create a second recovery loop. The existing graph continues through the normal verifier/reviewer path, and the local result is recorded as evidence. Verification can fail closed when the deterministic verifier itself is unsuccessful.

This keeps local execution an accelerator, not an alternate source of truth.