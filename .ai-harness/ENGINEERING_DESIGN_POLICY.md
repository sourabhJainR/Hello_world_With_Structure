# Engineering Design Policy

This policy distills the engineering intent of the 14 rule sets in `mattpocock/agent-rules-books` into one repository-native operating model. It is guidance for the AER system, not copied book text and not a substitute for the books.

## Source coverage

| Source | Constructive contribution to AER |
| --- | --- |
| A Philosophy of Software Design | Minimize cognitive load; prefer deep modules, information hiding, precise interfaces, localized complexity, and meaningful names. |
| Clean Architecture | Keep policy independent from frameworks and details; enforce inward dependencies and humble adapters. |
| Clean Code | Optimize for local readability, focused functions, explicit mutation, clear APIs, and behavior-focused tests. |
| Code Complete | Make construction deliberate: clear requirements, types, control flow, validation, diagnostics, incremental verification, and measured tuning. |
| Designing Data-Intensive Applications | Make ownership, consistency, durability, retries, replay, ordering, evolution, partitioning, replication, and repair semantics explicit. |
| Domain-Driven Design | Model domain language and invariants inside explicit bounded contexts; keep integration and persistence from defining the model. |
| Domain-Driven Design Distilled | Apply DDD selectively; invest in core domain complexity and avoid ceremony for simple CRUD or technical problems. |
| Implementing Domain-Driven Design | Protect aggregate boundaries, identity, value objects, repositories, domain events, application services, and translation boundaries. |
| Patterns of Enterprise Application Architecture | Choose patterns from actual forces; separate presentation, workflow, domain, persistence, transactions, concurrency, and integration. |
| Refactoring | Make behavior-preserving structural changes in small, reversible, verifiable steps. |
| Refactoring.Guru | Diagnose the smell first, choose the smallest treatment, preserve compatibility, and stop when the blocking smell is resolved. |
| Release It! | Design for failure, timeouts, bounded retries, isolation, overload, observability, safe deployment, and recovery. |
| The Pragmatic Programmer | Keep one source of truth, automate repeatable work, shorten feedback loops, own outcomes, and keep volatile choices reversible. |
| Working Effectively with Legacy Code | Gain control before redesign: characterize behavior, create small seams, break blocking dependencies, then change and refactor locally. |

## One integrated model

AER should not load all 14 sources as equal instructions on every task. They are capability lenses selected by task shape. The default integrated model is:

```text
INTENT
  -> MODEL
  -> BOUNDARIES
  -> OWNERSHIP
  -> CHANGE
  -> FAILURE
  -> VERIFY
  -> REVIEW
  -> RELEASE
  -> LEARN
```

### 1. Complexity and module design

For every non-trivial design or refactor, prefer lower cognitive load over lower line count. A new abstraction must hide meaningful complexity. Avoid pass-through layers, generic utility dumping grounds, speculative interfaces, exposed representation, temporal coupling, and boolean mode flags that force callers to understand internals.

### 2. Architecture and dependency direction

Keep business policy independent from frameworks, transports, persistence, vendors, and deployment details. Inner policy owns the interfaces it needs; outer adapters implement them. Organize by capability/use case/domain where that makes ownership clearer. Enforce important boundaries mechanically when practical.

### 3. Domain ownership

When domain complexity is material, define the bounded context and local vocabulary before shaping code. Keep invariants with the concept that owns them. Use entities, value objects, aggregates, domain services, repositories, and domain events only when they clarify real domain forces. Reference other aggregates by identity and translate foreign models at boundaries.

### 4. Enterprise pattern selection

Patterns are tools, not architecture by decoration. Select Transaction Script, Table Module, Domain Model, Service Layer, Repository, Data Mapper, Gateway, Unit of Work, Identity Map, DTO, facade, locking, and related patterns from concrete forces. Reject generic repositories, ORM-as-domain-model leakage, pass-through services, hidden transaction ownership, and remote object-shaped APIs.

### 5. Data and distributed-system semantics

Every important data flow must identify source of truth, derived data, consistency, durability, visibility, idempotency, ordering, schema evolution, failure recovery, and repair. Never assume exactly-once delivery, fresh replicas, reliable clocks, or successful remote calls merely because the API returned no immediate error. Caches, indexes, projections, and read models require rebuild and lag visibility.

### 6. Construction and code quality

Build in small verifiable increments. Use explicit names, narrow scopes, clear control flow, meaningful types, deliberate error handling, input validation at trust boundaries, and tests that cover normal, boundary, invalid, and failure behavior. Comments explain rationale, contracts, constraints, or non-obvious facts; they do not narrate confusing code.

### 7. Refactoring and legacy change

Classify work as feature, bug fix, or refactor. For refactors, preserve observable behavior and use small transformations. For poorly understood code, characterize behavior first and create the smallest useful seam. Do not combine broad cleanup, redesign, and behavior change in one opaque patch. Temporary seams need a cleanup path.

### 8. Production resilience

Production readiness includes timeouts, bounded retries, backoff/jitter, bulkheads, circuit breaking where appropriate, finite queues, load shedding, validation of external responses, structured observability, safe startup/migrations, authorization, auditability, and rollback or roll-forward paths. Resource ownership and failure cleanup are explicit.

### 9. Pragmatic feedback and learning

Prefer reversible decisions when evidence is weak. Use tracer slices or time-boxed prototypes to test expensive assumptions. Automate repeated checks. Keep one authoritative source for each system fact. A learning candidate may improve routing or context selection only after regression and safety evidence; it may never weaken security, permission, approval, or immutable safety controls.

## Conflict handling

When guidance pulls in different directions, use this order:

1. Repository/team instructions and acceptance criteria.
2. Security, privacy, permissions, and human approval boundaries.
3. Correctness and explicit contracts.
4. Existing maintained architecture and ownership.
5. Operational and data-safety requirements.
6. Complexity reduction and maintainability.
7. Minimal implementation cost.

Known compatibility constraints from the source collection must also be respected. In particular, DDD and IDDD should not be combined with enterprise patterns that directly contradict their domain ownership model; where a pattern conflicts with the chosen domain architecture, select the domain model and adapt the enterprise mechanism at the boundary.

## Required design evidence

For substantial changes, the run should capture only the evidence relevant to the task:

- responsibility/ownership and affected boundary;
- alternatives considered for material architecture decisions;
- source of truth and data consistency semantics when data changes;
- failure model, timeout/retry/recovery behavior when external or asynchronous work changes;
- behavior delta and safety net when changing existing code;
- domain language/context and invariant ownership when domain complexity changes;
- compatibility and rollout path for public or persisted contracts;
- verification performed and remaining uncertainty.

A missing dimension is acceptable when the guard records `not_applicable` with a reason. The goal is useful engineering evidence, not ceremony.

## Enforcement

`portable/engineering_design_guard.py` provides the deterministic design-contract gate. It infers relevant dimensions from intent and changed paths, validates declared design evidence, emits findings, and creates a content-addressed receipt suitable for the existing evidence/provenance chain.

The guard is advisory for low-risk work and blocking only when a configured gate requires a missing safety-critical contract. It never executes code, grants permissions, or performs external side effects.
