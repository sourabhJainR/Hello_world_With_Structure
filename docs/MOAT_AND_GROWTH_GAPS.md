# Moat, Adoption and Growth Gap Review

## Executive assessment

The project has a strong engineering philosophy, but philosophy alone will not make it indispensable. The missing layer is a product-grade operating system around the philosophy: durable state, measurable proof, low-friction onboarding, host adapters, team learning, and a visible quality signal.

The current competitive landscape is moving toward agent runtimes that combine tools, skills, context management, security, persistence, and provider abstraction. OpenHands is a useful benchmark: its SDK separates agent reasoning, tools, workspace, events, skills, context condensation, and security, while keeping the agent loop stateless and interruptible. citeturn0search0turn0search1

## Critical gaps

### 1. The Engineering State Ledger is conceptual, not yet a first-class artifact

Current state:

`INTENT -> CONTRACT -> REPO_FACTS -> DECISIONS -> EVIDENCE -> CHANGESET -> VERIFY -> OPEN_RISKS -> NEXT`

Gap:

- no canonical versioned schema;
- no lifecycle transitions;
- no merge/conflict rules across sessions or agents;
- no machine-readable provenance contract;
- no portable serialization contract;
- no clear retention/redaction policy.

Action:

Create `state/engineering-state.schema.json` and a reference implementation. Make state append-only where possible, immutable for evidence, and explicitly versioned. Allow compaction into a small checkpoint without losing provenance.

### 2. Evidence needs a first-class protocol

Research and flow analysis are strong conceptually, but the system needs a common evidence object:

`source -> locator -> snapshot/version -> claim -> confidence -> freshness -> provenance`

This is a major moat. A model response is not evidence. A repository line, test result, git commit, runtime observation, or authoritative external source is evidence.

Action:

Create an Evidence Contract and require material decisions to reference evidence IDs.

### 3. Proof should become a product primitive

The system currently emphasizes verification, but should expose a standard `Proof Bundle`:

- requirement IDs;
- changed files/symbols;
- tests run and results;
- static analysis;
- compatibility checks;
- security checks when relevant;
- runtime evidence when relevant;
- unresolved risks;
- reviewer findings;
- exact commit/diff identity.

This becomes the artifact that makes AI coding auditable rather than merely impressive.

### 4. No strong quality score yet

Add a task outcome score based on evidence, not model confidence:

`Correctness + Spec Fidelity + Regression Safety + Architecture + Operations + Security + Evidence Quality + Efficiency`

Report gaps rather than hiding them behind a single number. Track `time-to-proven-change` as the primary productivity metric.

### 5. Learning loop needs team-level memory

The system has evals and learning principles, but the moat needs a controlled organizational learning loop:

`failure/review -> normalized lesson -> regression eval -> candidate policy -> eval -> promotion`

Never turn raw model output or a single successful task into policy automatically.

### 6. Missing repository fingerprint

The first run should produce a compact `Repository Engineering Profile`:

- language/frameworks;
- build/test commands;
- source layout;
- dependency conventions;
- exception/error handling;
- logging/telemetry;
- test patterns;
- API/data contracts;
- deployment model;
- architecture boundaries;
- risky areas;
- repository instructions;
- confidence and evidence freshness.

Cache it with invalidation based on changed files/configuration, rather than re-discovering the repository every task.

### 7. Missing explicit task risk model

Add a deterministic risk vector:

`scope, blast_radius, reversibility, data_risk, security_risk, production_impact, contract_risk, uncertainty`

Risk determines whether the system should require stronger grilling, fresh-context review, sandboxing, broader tests, or explicit approval.

### 8. Back-and-forth is not yet treated as a measurable failure

Track:

- clarification rounds;
- requirement restatements;
- repeated tool calls;
- repeated failed tests;
- agent resets;
- abandoned plans;
- user corrections.

Create a `friction budget`. The system should proactively produce a concise clarification package when ambiguity is detected instead of asking one question at a time.

### 9. Missing "one-shot task contract"

For Jira/prompt input, generate a compact proposal:

`Goal | Non-goals | Requirements | Protected behavior | Acceptance | Risks | Questions`

Ask the user to correct only the disputed fields. This reduces back-and-forth substantially.

### 10. Host interoperability is not yet a real adapter contract

The system should define a host-neutral interface for:

- discover skill;
- read/write files;
- execute commands;
- inspect git;
- ask/confirm;
- retrieve evidence;
- persist state;
- report progress;
- emit telemetry;
- enforce permissions.

Claude Code, Codex, Gemini, OpenHands and future hosts become adapters. Do not fork the core behavior per host.

### 11. Optional integrations need capability negotiation

Graphify, code-mem, Ponytail, Superpowers, Caveman and other extensions should advertise:

`capability, version, health, cost, evidence type, freshness, failure mode`

The router chooses an extension only when it improves expected outcome enough to justify its cost.

### 12. Security needs to become risk-aware execution control

OpenHands explicitly places security analysis before tool execution and supports confirmation for high-risk actions. citeturn0search0turn0search2

Adopt a host-neutral policy model:

`observe < read < local write < dependency change < destructive operation < production/external side effect`

Each level has default approval, sandbox, logging, rollback and verification rules.

### 13. Context management needs adaptive compression

OpenHands uses condensers to reduce history as context grows. citeturn0search0turn0search3

Our FlashAttention-inspired context principles should evolve into a real policy:

- stable repository facts are cached;
- stale evidence is invalidated;
- repeated evidence is deduplicated;
- decisions are summarized, not transcripts;
- only task-relevant graph neighborhoods are expanded;
- review context is independent from author reasoning where practical.

### 14. No marketplace-quality trust layer

To become popular, users need to know what a skill/extension can do before enabling it.

Every extension should publish:

`purpose, triggers, permissions, tools, data access, side effects, dependencies, cost, version, license, eval score, failure behavior`

This becomes a trust manifest.

### 15. No compelling first-minute experience

Installation must be followed by immediate proof of value.

Target:

`install -> open repo -> run health/profile -> receive useful findings in <5 minutes`

Do not require users to configure Graphify, code-mem, MCP, model routing, or telemetry before the first useful result.

## The moat

The moat should be built around assets that improve with usage and are hard to reproduce by adding another prompt.

### Moat 1: Engineering Memory Graph

Combine:

`repository topology + decisions + evidence + failures + reviews + verified changes`

The important unit is not a code chunk. It is an engineering fact with provenance and lifecycle.

### Moat 2: Proof Graph

Link:

`requirement -> evidence -> decision -> change -> test -> review -> outcome`

Over time this becomes a searchable history of why the system behaves as it does.

### Moat 3: Regression Genome

Every escaped defect, bad agent decision, review rejection, and user correction can become a normalized eval. The system gets harder to fool over time.

### Moat 4: Repository DNA

Learn stable project-specific engineering patterns without learning unsafe or accidental behavior. The profile should distinguish:

`explicit rule / repeated convention / inferred pattern / unknown`

### Moat 5: Cross-agent portability

Keep the state, evidence, policy and proof above the model/host. This lets teams switch Claude, Codex, Gemini, OpenHands, or future models without losing accumulated engineering intelligence.

### Moat 6: Outcome economics

Optimize for:

`quality-adjusted time-to-proven-change`

not autonomous loops or raw token savings.

### Moat 7: Trustable autonomy

Autonomy should increase only when the system has evidence that a task class is safe. This creates an autonomy ladder:

`observe -> recommend -> edit -> test -> prepare PR -> autonomous bounded execution`

Each promotion requires eval evidence and policy approval.

## Product features that can make it indispensable

### A. "Tell me what is missing"

Before coding, detect missing requirements, acceptance criteria, boundaries, test cases, observability, migration implications and rollback considerations.

### B. "Explain before changing"

For risky changes, produce a short evidence-backed flow and impact map before mutation.

### C. "Do not surprise me"

Maintain explicit protected behavior and surface any proposed deviation before changing it.

### D. "One-click proof"

After implementation, produce the Proof Bundle automatically.

### E. "Continue from here"

A new model/session should resume from the Engineering State Ledger, not ask the user to restate the task.

### F. "Why did it do that?"

Every significant decision can be traced to evidence.

### G. "Learn from our reviews"

PR review findings become candidate regression cases, with promotion only after eval validation.

### H. "Works without setup"

Core operation requires no optional ecosystem dependency. Integrations improve results when available.

## Adoption strategy

### Individual developer

Value in first five minutes:

`profile -> understand -> fix -> prove`

### Team

Add:

`shared policies + repository DNA + PR proof + regression genome`

### Enterprise

Add:

`permissions + audit + data controls + private extension registry + model/provider routing + compliance evidence`

## North-star workflow

```text
Natural-language goal
        |
        v
One-shot task contract
        |
        v
Repository DNA + relevant evidence
        |
        v
Risk-adaptive plan
        |
        v
Minimal context
        |
        v
Execute with action policy
        |
        v
Observe + update state
        |
        v
Verify
        |
        v
Proof Bundle
        |
        v
Independent review when warranted
        |
        v
Regression Genome update
        |
        v
Durable handoff
```

## Priority roadmap

### P0 — Make the core indispensable

1. Engineering State Ledger schema.
2. Evidence Contract.
3. Proof Bundle.
4. One-shot task contract/grilling.
5. Repository Engineering Profile.
6. Deterministic risk model.
7. Friction/thrash metrics.

### P1 — Build the moat

8. Regression Genome.
9. Engineering Memory/Proof Graph.
10. Extension capability negotiation and trust manifest.
11. Host adapter contract.
12. Adaptive context cache/invalidation.

### P2 — Make it a platform

13. Team policy registry.
14. Private extension registry.
15. CI/PR integration.
16. Quality dashboard.
17. Cross-repository engineering learning with strict provenance and isolation.
18. Controlled autonomy ladder.

## Anti-goals

Do not win by becoming:

- a giant prompt;
- a mandatory multi-agent swarm;
- a model-specific wrapper;
- an always-running autonomous process;
- a noisy dashboard;
- an extension marketplace with untrusted arbitrary permissions;
- a memory dump of every repository and transcript.

The product should remain simple at the surface and rigorous underneath.

## Governing product principle

> Make the safe, evidence-backed path the easiest path for an engineer, while continuously reducing the amount of work the engineer must repeat to get a proven change.
