# Change Quality and Reuse Contract

## Goal

Make every AER-assisted repository change deliberately curated: reuse existing implementations where practical, preserve usage patterns, implement the complete requested behavior, minimize data-access cost, protect performance, follow local observability/error conventions, and verify against regressions before completion.

## Scope

This is a cross-cutting extension of the existing engineering-design gate and AI Coding Orchestrator. It does not introduce another workflow engine, memory store, repository index, evidence store, or policy authority.

## Design

### 1. Reuse-first change selection

Before creating a new abstraction, implementation, helper, client, query path, or utility, the run must record what existing implementations were inspected and why each candidate was reused, adapted, or rejected. A new implementation is justified only when an existing one cannot satisfy the requested behavior without harming correctness, compatibility, or maintainability.

Compatibility includes public API shape, calling conventions, data contracts, configuration behavior, lifecycle ordering, and user-visible workflow. Internal reuse may change, but externally observable usage should remain stable unless the request explicitly requires a breaking change.

### 2. Complete functionality coverage

Implementation plans must account for the requested happy path, validation, boundary cases, failure behavior, operational behavior, affected integrations, and tests. The smallest patch is preferred, but not at the expense of an incomplete requirement.

### 3. Data-access economy

When persistence or remote data access is involved, the design must state the source of truth and the intended access pattern. The implementation should reuse already-loaded data, batch compatible reads, avoid N+1 access, avoid duplicate round trips, preserve transaction semantics, and use established repository caching/batching mechanisms where present.

### 4. Performance parity

Performance-sensitive changes must identify the affected hot path and expected complexity/resource behavior. Avoid unnecessary allocations, repeated parsing/serialization, duplicate computation, blocking I/O, unbounded retries, and per-item network/database calls. Existing performance characteristics are treated as a compatibility constraint unless the request explicitly changes them.

### 5. Repository-native observability and exception handling

Logging and telemetry must follow the local repository convention, including framework, levels, structured fields, correlation/context, and redaction practices. Exception handling must use existing exception types and propagation/translation patterns, preserve diagnostic context, clean up owned resources, and avoid swallowing failures.

### 6. Regression protection

Every behavior change needs a proportionate safety net. Use existing tests first, then add focused tests for new behavior and affected failure/boundary paths. For material changes, run relevant integration/build/static/security/performance checks already native to the repository. A green new test alone is not sufficient evidence when existing workflows could regress.

### 7. Risk-aware enforcement

The existing `EngineeringDesignGuard` remains the single deterministic gate. The new practices are represented as additional design evidence keys and findings under its existing dimensions. Missing evidence remains advisory for low-risk work, while high-risk work blocks on missing reuse, regression, exception-handling, data-access, or performance contracts when those dimensions are relevant. Explicit `not_applicable: reason` is allowed.

## Non-goals

Do not create a second planner, workflow engine, quality database, repository index, logging abstraction, ORM/repository abstraction, benchmark framework, or compatibility layer. Do not change runtime behavior merely to support the gate.

## Verification

The change must include focused guard tests, preserve the existing test suite, validate the deployable orchestrator skill and repository instructions, and pass the complete repository CI matrix on the pull request before merge.
