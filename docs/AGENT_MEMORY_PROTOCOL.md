# Agent memory protocol

The orchestration uses three simple memory boundaries:

1. **Private agent memory** — owned by the execution agent. It is a small session-local notebook for useful working notes. It is never automatically promoted to team knowledge.
2. **Working task memory** — owned by the run. It contains bounded handoffs between agents and is disposable. Old entries are evicted when the budget is reached.
3. **Shared learning** — owned by the learning steward. The execution agent does not maintain this ledger. The steward records only explicit, evidence-backed observations about what worked, failed, regressed, or remained partial.

## Execution flow

```text
historical learning -> execution agent
                         |
                         +-> private memory (optional)
                         +-> bounded task handoff
                                   |
                                   v
                           learning steward
                                   |
                                   +-> shared learning ledger
                                   |
                                   v
                         current downstream agents
                                   |
                                   v
                         future task executions
```

The important separation is intentional: the agent doing the work stays focused on the work. Learning, retrospectives, and durable recording are peripheral responsibilities delegated to the learning steward.

Every agent receives a small retrieval of prior task learning. The retrieval is bounded and treated as evidence, not truth. Repository files and deterministic verification remain the source of truth.

Execution agents may optionally return a `## PRIVATE MEMORY` section. The orchestrator stores it only under that agent's private session memory. They must not write team-wide lessons there.

The learning steward returns a `## LEARNINGS` section with explicit observations such as:

```text
- failed | unsupported compiler flag | the legacy build rejects this flag
- worked | supported compiler flags | deterministic build passes
```

This protocol deliberately avoids a second summarization model, vector database, or transcript replay. Add those only if measured retrieval quality requires them.
