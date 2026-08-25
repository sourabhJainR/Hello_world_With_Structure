# Future Architecture

## Purpose

This document defines the evolution path for the Adaptive AI Coding Orchestrator without turning the core skill into a large prompt or a mandatory dependency graph.

## Design goals

- Keep the core provider-neutral and language-neutral.
- Treat Claude Code, Codex, Gemini CLI and future agents as adapters.
- Treat Graphify, code-mem and other tools as optional capability providers.
- Prefer repository evidence over model assumptions.
- Minimize context before increasing model reasoning effort.
- Make every important action observable and reproducible.
- Keep write and execution permissions least-privileged.
- Make extension failures degradable rather than fatal.
- Preserve deterministic routing and policy checks around probabilistic models.

## Capability architecture

```text
Agent adapter
    |
    v
Orchestrator
    |
    +-- Task classifier
    +-- Policy engine
    +-- Repository profiler
    +-- Knowledge fabric
    +-- Context budgeter
    +-- Workflow engine
    +-- Verification engine
    +-- Review engine
    +-- Learning/evaluation store
    |
    +-- Capability providers
          +-- AST
          +-- Graph
          +-- Memory
          +-- Search
          +-- Test/build
          +-- Static analysis
          +-- Observability
```

## Provider contract

Every optional provider should expose capabilities, health, cost and evidence quality. The orchestrator should select providers by capability rather than by product name.

A provider must be allowed to return `unavailable`, `degraded`, or `not-applicable`. The orchestrator must then fall back to another provider or a native repository mechanism.

## Policy before capability

The execution order is:

1. Load applicable repository and organization instructions.
2. Classify intent, scope and risk.
3. Establish permissions and prohibited actions.
4. Discover available capabilities.
5. Retrieve the smallest sufficient evidence set.
6. Execute the selected workflow.
7. Verify independently.
8. Review the diff and evidence.
9. Persist only useful, non-sensitive learning signals.

## Future capabilities

### Remote execution

Support isolated remote workspaces for builds, tests and generated migrations. Never require production access.

### Evaluation-driven routing

Use historical eval results to compare routing strategies and detect regressions before changing the default policy.

### Model routing

Allow a policy layer to choose a model based on task complexity, latency, cost and required context while keeping the workflow model-independent.

### Durable project memory

Persist architecture decisions, verified conventions and recurring failure patterns with provenance, confidence and expiry. Never persist secrets or raw sensitive source unless explicitly configured.

### Multi-agent delegation

Allow specialist agents to operate behind the same capability and evidence contracts. Avoid unconstrained agent-to-agent recursion.

### Change-risk prediction

Estimate risk from touched symbols, dependency fan-out, API/schema changes, historical defects and test coverage. Use this to increase verification, not to bypass it.

### Continuous evaluation

Maintain a small fast eval suite for every change and a larger scheduled regression suite. Compare accuracy, context size, tool calls, latency and cost.

## Non-goals

The core will not:

- install arbitrary third-party software automatically;
- silently change developer permissions;
- merge or deploy production changes without explicit policy;
- require a specific LLM provider;
- require Graphify or code-mem;
- recursively invoke itself without an explicit user request;
- retain sensitive repository content by default.

## Maturity gates

A new major capability should not become default until it has:

- a provider-neutral contract;
- deterministic unit tests;
- positive and negative eval cases;
- failure/degraded-mode behavior;
- context-budget measurements;
- security and permission review;
- documentation and rollback behavior.
