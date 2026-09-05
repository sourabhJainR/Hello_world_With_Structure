# Lifecycle Pack

Use only when the task needs orchestration detail.

`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

Use `Agent -> bounded Loop -> Graph -> Orchestration` only as complexity requires.

Every loop has explicit attempt/time/token/risk limits. Every graph node declares inputs, outputs, dependencies and mutation boundaries. Failed evaluators block dependent nodes unless a documented recovery path permits progress. Parallelize only independent read-only work.

Carry `intent_digest` through phases and handoffs. A handoff contains source, destination, phase, findings, decisions, open risks and next actions.

Recovery is evidence-driven: classify failure, preserve the failing evidence, change strategy, retry only when justified, and stop when the contract is no longer valid or the budget is exhausted.

For self-modification use:
`Candidate -> Regression -> Safety -> Shadow -> Canary -> Promote -> Monitor -> Rollback`.
