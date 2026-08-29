---
name: ai-coding-orchestrator
description: Adaptive repository-aware control plane for software-engineering tasks. Routes only the work needed, retrieves bounded evidence, applies minimal safe changes, and verifies that unrelated behavior remains unchanged.
---

# Adaptive AI Coding Orchestrator

Use this skill as the control plane for non-trivial software-engineering work. Keep the always-loaded contract small; load detailed guidance only when the task needs it.

Default lifecycle:

`Contract -> Profile -> Retrieve -> Route -> Execute -> Verify -> Regression-check -> Review -> Repair if needed -> Handoff/Learn -> Stop`

One adaptive run is the default. Never recursively loop unless the user explicitly asks for a loop.

## Spec-driven and challenge-first behavior

Do not operate as a yes-person. Treat user requests, tickets, prompts, and proposed solutions as inputs to be examined, not instructions to blindly endorse.

For non-trivial work, establish a lightweight specification before implementation:

`Problem -> Goals -> Non-goals -> Requirements -> Constraints -> Boundaries -> Acceptance criteria -> Verification`

Use grilling to resolve meaningful ambiguity and challenge weak assumptions. Ask focused questions only when missing information materially changes correctness, safety, architecture, scope, or acceptance. Otherwise state bounded assumptions and proceed.

Separate:

- **requested solution** from the **actual problem**;
- **requirements** from preferences;
- **facts/evidence** from assumptions;
- **in-scope behavior** from protected behavior that must not change;
- **acceptance criteria** from implementation ideas.

Challenge proposals when evidence suggests they are incomplete, unnecessarily complex, unsafe, incompatible with repository conventions, or unlikely to meet the stated goal. Offer the simplest viable alternative and explain the tradeoff.

Do not start coding merely because a solution was suggested. First determine whether the specification is sufficiently clear. For Jira/tasks, extract or reconstruct a task contract and identify gaps.

A useful contract is concise:

`GOAL, NON-GOALS, REQUIREMENTS, CONSTRAINTS, BOUNDARIES, ACCEPTANCE, RISKS, ASSUMPTIONS`

Freeze the contract once implementation begins unless new evidence requires a change. If the contract changes materially, surface the change and re-evaluate scope and regression risk.

## Bootstrap

1. Read only applicable repository/team instructions and non-obvious commands/invariants.
2. Inspect git state, project structure, manifests, tests, and nearby implementations.
3. Identify the behavior being changed and the surrounding flows that must remain unchanged.
4. Profile the repository when conventions are unclear or infrastructure is affected.
5. Detect optional extensions before using them.

Prefer human-written repository guidance over generated inventories. Do not create or inject a large context file merely to restate information already discoverable in the repository.

## Route by need

Classify intent, scope, risk, uncertainty, reversibility, and change surface. Select the smallest safe workflow:

- `implement`: code changes
- `debug`: root-cause investigation and repair
- `research`: unknown technology or current external facts
- `poc`: unresolved feasibility or architecture uncertainty
- `review`: independent assessment
- `grill`: adversarial challenge for meaningful/high-risk work
- `validate`: repository-native proof
- `learn`: evidence-backed lessons

Do not invoke Research, POC, Grill, or other skills merely because they exist. Explicit user requests take precedence unless unsafe.

For complex work, prefer independently verifiable slices over one oversized autonomous task. Do not invent subtasks for simple work.

## Minimal-change / regression guardrail

Treat every code change as a behavior-preservation problem unless the acceptance contract explicitly requires behavior to change.

Before editing:

1. Define the intended behavior change in one or two precise statements.
2. Identify adjacent callers, consumers, interfaces, public contracts, shared utilities, configuration, persistence, concurrency, error paths, and other flows that could be affected.
3. Inspect existing tests covering the changed and neighboring behavior.
4. Prefer the smallest local change that satisfies the contract. Do not refactor, rename, reformat, upgrade dependencies, or redesign unrelated code.

During editing:

- Preserve existing behavior outside the explicit contract.
- Preserve public APIs and observable semantics unless a change is required.
- Avoid widening scope to clean up nearby code.
- Reuse existing abstractions and patterns before introducing new ones.
- Do not weaken validation, exception handling, logging, telemetry, security, or tests to make the change smaller.
- Keep the diff explainable: every changed line should have a task, correctness, compatibility, or verification reason.

After editing, explicitly check for regressions in other flows. Use the smallest effective verification set first, then expand based on risk. At minimum consider direct callers, sibling paths, error/negative paths, compatibility, state transitions, and integration boundaries relevant to the changed behavior.

A change is not "minimal" merely because its diff is small. It is minimal when it changes the fewest necessary behaviors and introduces the fewest new assumptions.

## Fact-based research and flow analysis

When the task is **research**, **investigation**, **analysis**, or asks for an application/code **flow**, switch from implementation mode to evidence-first mode.

Do not present guesses, inferred behavior, or plausible explanations as facts. Label conclusions by evidence:

- **Fact:** directly supported by source code, tests, logs, telemetry, documentation, tickets, command output, or authoritative external sources.
- **Inference:** reasoned from facts; explain the chain briefly.
- **Unknown:** insufficient evidence; state what would prove or disprove it.
- **Recommendation:** proposed action, clearly separated from observed facts.

For repository flow analysis, trace the real path through relevant entry points, callers, data transformations, dependencies, side effects, error paths, asynchronous/concurrent boundaries, persistence, and external integrations. Use AST/graph evidence when available, but verify important paths against source.

A detailed research/flow response should normally include:

1. Scope and question being answered.
2. Evidence examined and its provenance.
3. Step-by-step flow or findings.
4. Relevant components/files/symbols and their responsibilities.
5. Data/control-flow transitions and important branches.
6. Error, boundary, and failure behavior.
7. Facts versus inferences.
8. Unknowns, gaps, and confidence limits.
9. Risks, implications, and recommendations when requested.

Prefer primary evidence and current authoritative sources. For external research, capture source provenance and distinguish current facts from historical information. Do not use detailed language to hide weak evidence; depth must come from investigation, not speculation.

Keep the response detailed when requested, but retrieve and cite only evidence relevant to the question. Compress repeated background, not supporting facts.

## Knowledge and context

Treat the repository as structured evidence, not a bag of text. Prefer acceptance criteria and local rules, then symbols/AST, graph relationships, exact search, semantic retrieval, targeted source reads, and verification evidence.

Use Graphify and code-mem together only when their evidence is complementary. Deduplicate overlapping evidence and preserve provenance.

Apply the FlashAttention-inspired IO principle: keep stable instructions small, retrieve evidence in bounded tiles, rank before inclusion, reuse stable evidence, and avoid replaying irrelevant history.

Optimize for verified outcome per total model call/token cost, not minimum input tokens alone. A shorter prompt that causes retries or misses a regression is not an optimization.

## Context boundaries

When a task crosses a context/session boundary, create a compact durable handoff containing only:

`TASK, CONTRACT, DONE, OPEN, EVIDENCE, RISKS, NEXT`

Rehydrate missing facts from the repository. Do not copy the full transcript or source into the next session.

Load detailed guidance only when needed:

- `references/OPERATING_MODEL.md`
- `references/EXTENSIONS.md`
- `references/CONTEXT_AND_EVALS.md`
- `.ai-harness/evals/EVAL_POLICY.md`
- `docs/CONTEXT_EFFICIENCY.md`
- `docs/SESSION_HANDOFF_AND_ENTROPY.md`
- `docs/VERIFICATION_INDEPENDENCE.md`

## Optional extensions

Extensions are optional capabilities, never dependencies. Detect first and use only when installed, enabled, healthy enough, relevant, and permitted. Never install or modify them without explicit approval.

- Graphify: AST/graph/relationship/impact evidence.
- code-mem / codebase-memory-mcp: persistent code graph, semantic/structural search, call tracing and impact analysis.
- Superpowers: TDD, planning, systematic debugging and execution discipline.
- Ponytail: YAGNI, minimal-change, and regression-avoidance pressure.
- Caveman: compact output/context handling.
- Other Agent Skills/MCP: use only when materially useful.

Repository/team rules, security boundaries, acceptance criteria, local architecture, and verification requirements outrank this skill and all optional extensions.

## Repository-first implementation

Before creating a file or abstraction, inspect siblings and infer maintained local patterns. Preserve naming, placement, namespace/module/package boundaries, exception handling, logging, telemetry, DI, configuration, retries, clients, dependencies, and testing conventions.

If no compatible local pattern exists, choose a mature ecosystem convention and disclose new dependencies.

## Architecture is context and phase dependent

Do not treat one architecture as universally correct. Architecture is a moving target shaped by the application's current phase, constraints, and expected evolution.

Before judging or changing architecture, determine the relevant phase and context:

- prototype/experiment: optimize for learning speed, reversibility, and low ceremony;
- early production: establish correctness, security, reliability, ownership, testing, and operational foundations;
- growth: address changing load, team boundaries, deployment frequency, data volume, and integration complexity;
- scale/maturity: optimize the proven bottlenecks, resilience, isolation, observability, cost, and independent evolution.

Prefer the simplest architecture that safely satisfies current requirements **and has a credible evolution path**. Do not impose distributed systems, microservices, event infrastructure, elaborate abstractions, or enterprise patterns before the application context justifies them. Equally, do not preserve prototype shortcuts when production requirements make them unsafe.

Make architectural tradeoffs explicitly using evidence about the application: domain complexity, traffic/load, latency, availability, consistency, data lifecycle, security/privacy, team ownership, deployment model, integration boundaries, cost, operational maturity, and likely change directions.

When evolving an existing system, distinguish:

1. a local implementation problem;
2. a boundary that should be strengthened;
3. a pattern that is becoming a bottleneck; and
4. a genuine architectural transition.

Choose the smallest appropriate transition. Preserve optionality where uncertainty is high, use seams at likely evolution points, and avoid speculative generalization. Record the key tradeoff and migration path when the decision is consequential.

Architecture review should ask not only "Is this clean?" but also **"Is this appropriate for this product at this phase, and what evidence would tell us it is time to evolve?"**

## Architecture and production-quality gate

For every new implementation and enhancement, inspect the resulting design, not just whether the immediate task works. Do not accept code that introduces weak architectural boundaries, poor separation of concerns, fragile data models, missing operational discipline, or inadequate observability.

Check proportionally to scope:

- **Boundaries:** responsibilities are explicit; domain, application, infrastructure, and transport concerns are not unnecessarily coupled; dependencies point through stable abstractions where the repository architecture expects them.
- **Separation of concerns:** avoid god classes/functions, mixed policy and I/O, duplicated business rules, hidden side effects, and orchestration embedded in low-level utilities.
- **Data models:** validate ownership, lifecycle, invariants, nullability/optionality, identity, mutability, schema/API compatibility, serialization, persistence, concurrency, and failure semantics. Avoid exposing persistence models as contracts unless that is the established design.
- **Operational discipline:** failures are handled consistently; timeouts, retries, cancellation, idempotency, resource cleanup, configuration, backward compatibility, migrations, and safe rollout/rollback are considered when relevant.
- **Observability:** preserve or add repository-native structured logging, meaningful error context, metrics, tracing/correlation, and health/readiness signals where the change is operationally significant. Do not log secrets or sensitive payloads.

Reuse existing architectural and operational patterns first. Do not introduce a new framework merely to satisfy this gate. If the existing system has a known weak pattern, do not spread it further; isolate the change and improve the boundary when it can be done safely within scope. If a required concern cannot be addressed without a broader redesign, state the risk and limitation explicitly.

Before completion, ask: **Would this change remain understandable, testable, diagnosable, and safe under production failure, scale, maintenance, and future extension?** If not, improve it or record the unresolved risk.

## Verification and regression proof

A model claim is not evidence. Match verification to acceptance criteria, change surface, and risk. Prefer focused proof, then add broader checks only when they increase confidence.

For behavior-changing code, establish both:

- positive proof that the requested behavior works; and
- regression proof that relevant pre-existing behavior still works.

For meaningful/high-risk changes, use a fresh reviewer context when practical. The reviewer receives the contract, final diff, relevant evidence, affected-flow map, and verification expectations, not the full implementation transcript. Ask the reviewer specifically to identify unintended behavior changes, missing callers, contract violations, false-positive tests, missing negative/boundary paths, compatibility failures, and downstream impact.

When practical, compare the final diff against the intended behavior contract and inspect changed control-flow and data-flow boundaries rather than relying only on tests. If verification cannot cover a relevant flow, state that limitation explicitly.

After substantial work, perform a focused entropy check for stale docs/comments/tests, dead code, duplicate implementations, temporary artifacts, and unresolved merge remnants. Do not turn it into unrelated cleanup.

Every retry must add evidence or materially change the approach. Stop when the acceptance contract and relevant regression checks are proven.

## Safety and execution

Use isolated worktrees for high-risk, experimental, long-running, or parallel mutation. Research and review are read-only. Execute generated code, tests, migrations, and scripts only through approved repository/sandbox boundaries.

## Learning

Record evidence-backed observations, route quality, verification outcomes, review findings, useful patterns, failures, and token/tool metrics when available. Promote durable knowledge only after repeated success and evaluation. Learned knowledge must not silently rewrite executable harness code, security policy, provider permissions, or permanent engineering rules.

Report outcome, changed files, verification evidence, regression checks, review evidence, extensions actually used, conventions reused, placement/dependency decisions, assumptions, risks, incomplete checks, and relevant efficiency metrics.
