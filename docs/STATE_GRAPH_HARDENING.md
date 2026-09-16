# State Graph Hardening

`portable.agency_state_graph.StateGraph` is the single bounded workflow engine.

Runtime state and node outputs are JSON-compatible and canonically serialized, so mapping order cannot change digests. Checkpoints carry a verified state digest and reject corrupted state. Nodes declare `pure`, `idempotent`, or `external` effects; external effects are not retried by default. Retry policies may restrict exception classes. Per-node timeouts return control to the caller without waiting for the worker, while parallel results remain merged in graph order.

The executor owns workflow mechanics only. Repository truth remains `CodebaseIndex`, planning remains `TaskPlan`, evidence remains the engineering-state ledger, capabilities remain `CapabilityFabric`, and verification/release remain downstream authorities.
