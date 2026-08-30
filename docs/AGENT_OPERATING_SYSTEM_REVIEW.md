# Competitive Architecture Review: Toward a Software Engineering Operating System for Agents

## Scope

This review compares the ecosystem against nearby agent platforms and coding-agent harnesses, then identifies capabilities worth adapting without turning the project into a clone.

Reviewed reference systems include:

- OpenHands Software Agent SDK and its skills/context architecture.
- SWE-agent and its Agent-Computer Interface design.
- Aider and its repository-map approach.
- Factory/Droid and its multi-surface SDLC automation model.
- The existing AI Hero skills ecosystem already reviewed separately.

## What the current system already does well

The orchestrator already has a strong foundation:

- spec-driven, challenge-first execution;
- repository-first conventions;
- evidence-first research and flow analysis;
- bounded context and progressive disclosure;
- optional Graphify/code-mem intelligence;
- minimal-change and regression discipline;
- phase-aware architecture evolution;
- production architecture, operations, and observability gates;
- provider-neutral extension model;
- deterministic eval and safe learning boundaries.

The biggest remaining gap was not another specialist skill. It was a stronger **runtime operating model** that preserves task intent and evidence across tools, sessions, and models while preventing thrash.

## Adapted capabilities

### 1. Stateless runtime with one durable source of task state

OpenHands separates agent execution from application surfaces and treats context/state deliberately. The adaptation is an Engineering State Ledger:

`INTENT, CONTRACT, REPO_FACTS, DECISIONS, EVIDENCE, CHANGESET, VERIFY, OPEN_RISKS, NEXT`

This creates continuity without replaying transcripts.

### 2. Action-observation discipline

SWE-agent demonstrates that the interface between agent and computer materially affects quality. The adaptation is explicit action gates and evidence-bearing observations.

Every significant mutation should answer:

- Why is this action needed?
- What evidence triggered it?
- What changed?
- What observation updated the task state?

### 3. Repository topology before raw source volume

Aider's repository map demonstrates the value of concise structural context. The adaptation is already compatible with Graphify/code-mem:

- maintain a compact symbol/topology view;
- retrieve detailed source only for relevant paths;
- rank and deduplicate evidence;
- avoid full repository dumps.

### 4. Stuck/thrash detection

Modern agent runtimes increasingly treat repeated non-progress as a runtime failure mode.

The orchestrator now requires:

`observe repeated non-progress -> stop -> summarize -> reduce -> change strategy -> continue only with new evidence`

This is critical for token efficiency and predictable user experience.

### 5. Independent work in fresh contexts

Factory's distinction between inline skills and separate subagents reinforces an important boundary:

- use inline guidance for lightweight procedures;
- use a fresh context when independence, alternate reasoning, or strict isolation adds value.

The orchestrator should not spawn agents by default. Parallelism must earn its coordination cost.

### 6. Multi-surface portability

OpenHands and Factory demonstrate the value of running the same engineering model across CLI, application, automation, and remote environments.

The moat here is a host-neutral contract:

`User intent -> Engineering State Ledger -> Policy/routing -> Evidence -> Actions -> Proof`

Claude Code, Codex, Gemini CLI, OpenHands/ACP, CI workflows, and future hosts should be adapters around that contract rather than forks of the engineering behavior.

## The moat

The defensible layer should not be "better prompts." Models will commoditize that.

Build the moat around five compounding assets:

### A. Engineering State Ledger

Portable, compact, evidence-linked task memory that survives model and session changes.

### B. Repository Intelligence Fabric

A provider-neutral evidence layer combining repository rules, topology, AST/graph, exact search, semantic memory, runtime evidence, and verification.

### C. Evidence-to-Decision Traceability

Every meaningful change can answer:

`requirement -> evidence -> decision -> diff -> verification`

This makes the system reviewable and enterprise-friendly.

### D. Regression Knowledge

Failures, false assumptions, and review findings become deterministic eval cases. The system improves by reducing known failure modes rather than merely accumulating prompt text.

### E. Workflow Economics

Measure useful outcome against:

- model calls;
- tokens;
- latency;
- retries;
- tool failures;
- verification failures;
- unnecessary clarification rounds.

The target metric is **time-to-proven-change**, not autonomous activity.

## Productivity and back-and-forth reduction

The default UX should be outcome-first:

`"Fix tenant export duplication without changing existing API behavior."`

The system should infer the workflow and ask questions only when ambiguity changes correctness, safety, scope, architecture, or acceptance.

For long work, expose short checkpoints:

`UNDERSTOOD -> INVESTIGATING -> PLAN -> CHANGED -> PROVEN -> OPEN_RISKS`

This reduces the common agent failure modes:

- users repeatedly restating requirements;
- agents forgetting boundaries;
- context resets losing decisions;
- speculative implementation;
- repeated non-progress loops;
- late discovery of regressions.

## Product architecture target

```text
                         USER / JIRA / CI EVENT
                                  |
                                  v
                          Intent + Contract Layer
                                  |
                                  v
                       Engineering State Ledger
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
           Policy / Routing                  Evidence Fabric
                 |                      rules / topology / AST
                 |                      graph / search / memory
                 +----------------+----------------+
                                  |
                                  v
                            Action Gates
                    understand / plan / change / proof
                                  |
                                  v
                       Host / Agent Adapter Layer
             Claude | Codex | Gemini | ACP | CI | future hosts
                                  |
                                  v
                       Execute -> Observe -> Verify
                                  |
                                  v
                    Independent Review / Risk Check
                                  |
                                  v
                         Evals + Regression Knowledge
```

## Non-goals

Do not:

- build a mandatory multi-agent swarm;
- force every task through every stage;
- create a proprietary dependency around one model;
- make persistent autonomous loops the default;
- replace existing repository conventions with the orchestrator;
- collect large transcript memories;
- optimize token count at the expense of proof.

## Recommended next implementation priorities

1. Formalize the Engineering State Ledger as a portable schema.
2. Add deterministic evals for thrashing, missing evidence, and unnecessary clarification.
3. Add host adapters that map Claude Code/Codex/Gemini/OpenHands capabilities into one contract.
4. Build a repository-intelligence cache with provenance and invalidation rules.
5. Add a "time-to-proven-change" telemetry model.
6. Add an optional CI/PR mode that consumes the same ledger and proof artifacts.
7. Publish extension contracts so external skills/providers can contribute evidence without polluting core context.

## Governing principle

> The system should make the right engineering path easier than the wrong one, while staying simpler for the user than the engineering work it coordinates.
