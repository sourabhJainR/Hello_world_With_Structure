# Engineering quality and reuse

Use `.ai-harness/ENGINEERING_DESIGN_POLICY.md` and `portable.engineering_design_guard.EngineeringDesignGuard.review(...)` for substantial implementation.

For code changes, make this evidence explicit:

`reuse candidates -> usage compatibility -> data/DB access -> performance -> logging/telemetry -> exception handling -> regression safety net`

## Reuse before creation

Search first for existing implementations, extension points, interfaces, helpers, clients, repositories, query paths, tests, configuration, loggers, and exception types serving the same responsibility. Prefer reuse, composition, narrow extension, or adapters over duplication. When reuse is rejected, record the candidate and concrete reason.

## Preserve usage patterns

Treat existing API shapes, caller behavior, configuration semantics, persisted contracts, lifecycle ordering, CLI/HTTP flows, and user-visible workflows as compatibility surfaces. Keep them unchanged unless the request explicitly requires a contract or behavior change.

## Minimize data and database calls

Inspect the existing data-access path before adding one. Prefer already-fetched state, existing caches, batching/set-based operations, joins or bulk APIs already used, and shared transaction/connection handling. Avoid N+1 queries, per-record reads, duplicate round trips, repeated hydration, and needless remote calls without weakening correctness or consistency.

## Keep performance at parity

Identify hot paths and resource-sensitive behavior. Preserve expected latency, throughput, CPU, memory, allocation, I/O, concurrency, and queue characteristics unless the request intentionally changes them. Reuse existing pooling, batching, caching, serialization, and scheduling. Measure when static reasoning cannot establish parity safely.

## Logging and exceptions

Use the repository's logger/telemetry framework, severity levels, structured fields, correlation/context, redaction, and sampling rules. Reuse existing exception types and propagation/translation patterns, preserve diagnostic context, clean up owned resources, and never swallow failures. Do not introduce a second logging/error abstraction.

## Regression

Verify the new requirement and affected existing behavior. Start with focused tests, then run relevant repository-native build, integration, contract, static, security, data, and performance checks. A new test passing does not prove an existing workflow was preserved.

`not_applicable: reason` is valid for a genuinely irrelevant concern; silent omission is not evidence. Higher-risk code changes block when configured quality/safety evidence is missing.
