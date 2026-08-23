# Language-Neutral Engineering Principles

These principles are reasoning rules, not language-specific coding rules. Apply them proportionally to the task, repository, risk, and compatibility constraints.

## Core principles

### DRY — Don't Repeat Yourself
Keep each piece of knowledge in one authoritative place when duplication creates drift or inconsistent behavior.

Do not turn harmless repetition into forced abstraction. Prefer duplication over a premature abstraction when the repeated code is small, unstable, or not semantically related.

### YAGNI — You Aren't Gonna Need It
Implement the smallest capability required by the current requirement and acceptance criteria. Do not add speculative extension points, configuration, abstractions, or infrastructure without a concrete need.

### KISS — Keep It Simple
Prefer the simplest design that meets the requirements, constraints, reliability needs, and expected scale.

### DI — Dependency Inversion / Dependency Injection
Depend on stable contracts rather than concrete volatile details. Make meaningful external dependencies replaceable where this improves testing, isolation, configuration, or changeability.

Do not introduce a dependency-injection framework merely to satisfy the acronym. Constructor injection, function parameters, factories, interfaces, protocols, modules, or equivalent language mechanisms are all valid.

### SOLID
Apply the principles selectively, not mechanically:

- Single Responsibility: keep unrelated reasons to change separate.
- Open/Closed: prefer extension points when recurring change justifies them; avoid speculative abstraction.
- Liskov Substitution: substitutable implementations must preserve the contract and behavioral expectations.
- Interface Segregation: keep contracts focused on what consumers need.
- Dependency Inversion: stable policy should not depend directly on volatile infrastructure.

### Separation of Concerns
Keep business rules, orchestration, state, persistence, transport, presentation, and infrastructure concerns appropriately separated for the repository architecture.

### High Cohesion, Low Coupling
Keep closely related behavior together while minimizing unnecessary dependencies between unrelated components.

### Composition over Inheritance
Prefer composition, delegation, and explicit collaboration when they reduce coupling or make behavior easier to test and change. Use inheritance when the domain truly expresses a stable substitutable relationship.

### Principle of Least Knowledge
A component should know only what it needs about collaborators. Avoid unnecessary traversal through object graphs or knowledge of internal implementation details.

### Fail Fast and Explicitly
Detect invalid input, impossible states, and violated invariants as early as practical. Prefer clear failures over silent corruption or surprising fallback behavior.

### Single Source of Truth
Avoid multiple independently maintained sources for the same business or configuration knowledge. Derive secondary representations where practical.

### Least Surprise
Prefer behavior, naming, defaults, and interfaces that are consistent with repository conventions and reasonable user expectations.

### Make Illegal States Hard to Represent
Use validation, types, contracts, invariants, state machines, or equivalent mechanisms to prevent invalid states instead of repeatedly checking them after the fact.

### Compatibility by Default
Preserve existing public behavior, data contracts, persistence expectations, and integrations unless the task explicitly requires a breaking change.

### Test the Behavior
Tests should prove meaningful behavior, contracts, failure modes, and regressions. Do not optimize for line coverage at the expense of useful evidence.

### Observability
For production-relevant behavior, make important failures and state transitions diagnosable through appropriate logs, metrics, traces, or equivalent mechanisms.

### Security by Default
Validate untrusted input, minimize permissions, protect secrets, avoid unsafe defaults, and treat authentication, authorization, data exposure, injection, and trust boundaries as explicit design concerns.

### Resource and Failure Awareness
Consider time, memory, concurrency, I/O, retries, partial failure, cancellation, idempotency, rate limits, and cleanup when the task can affect them.

### Reversibility
Prefer changes that are easy to roll back or disable. For high-risk changes, identify migration, rollback, and failure-recovery paths before implementation.

### Evidence over Assumption
Prefer repository evidence, tests, specifications, measured behavior, and verified documentation over guesses. Clearly label assumptions.

### Locality of Change
Change the smallest relevant surface area. Avoid unrelated refactoring unless it directly reduces risk or is required to make the change correct.

## Decision rule

Apply principles as constraints, not rituals:

1. Start with task intent and acceptance criteria.
2. Inspect existing repository patterns.
3. Identify the principles that materially affect the decision.
4. Prefer the smallest design satisfying those principles.
5. Explain intentional deviations when a principle conflicts with compatibility, performance, simplicity, or task scope.
