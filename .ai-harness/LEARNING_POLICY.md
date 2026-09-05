# Learning and Evolution Policy

Learning is evidence accumulation governed by a promotion state machine, not unrestricted self-modification.

## Learning lifecycle

```text
experience -> candidate -> regression replay -> shadow -> staged canary -> active -> monitor -> rollback
```

A single model output is an observation only. The durable experience store is the source of truth for candidate scoring. A later regression or missed behavior is a high-value negative observation and remains linked to the original task/run.

## Experience and scoring

Each experience records task family, strategy, success, acceptance, verification, retries, regressions, cost, latency, safety, evidence quality, environment/policy lineage and failure class. Candidate scores combine these outcome signals with an uncertainty-aware Wilson lower bound. Small samples must not win merely because their observed success rate is high.

## Task-family regression selection

Regression replay is selected by task family. Known historical failures and recent failures receive priority, followed by representative same-family cases and bounded neighboring-family coverage. Selection is deterministic and fingerprinted so promotion decisions are reproducible.

## Promotion gates

A candidate may become active only after:

1. sufficient historical experience;
2. meaningful improvement over the incumbent;
3. regression replay passes;
4. independent shadow evaluation passes;
5. every staged canary gate passes;
6. candidate risk and confidence are acceptable;
7. policy lineage and evidence are persisted atomically.

The learning engine may propose executable orchestration changes, but it never grants permissions, credentials, security exemptions, or approval authority to itself.

## Rollback

After activation, acceptance degradation or increased regression rate triggers automatic rollback to the previous known-good policy. The failed policy remains recorded for analysis and future learning; rollback never deletes evidence.

## Regression learning

When a completed task later produces a related regression or miss:

1. record the original run ID and immutable intent digest;
2. capture the reported symptom and evidence IDs;
3. keep the event separate from the product patch;
4. run analysis/RCA first when requested;
5. add the failure as negative learning evidence;
6. require repeated evidence and successful future verification before trusting a corrective pattern.

A regression report never authorizes an automatic product change.

## Immutable zones

Learned memory must never directly modify:

- executable harness permissions or security boundaries
- provider credentials or permissions
- security and approval policy
- dependency allowlists
- repository architecture rules

Those changes require the normal implementation, verification, and review path. Candidate executable orchestration is evaluated inside the designated evaluation boundary before activation.

## Learning targets

Prefer learning routing, retrieval, context selection, verification strategy, failure handling, repair strategy, regression avoidance, task boundaries and token/tool efficiency. Never optimize raw speed when correctness, safety or verification quality gets worse.
