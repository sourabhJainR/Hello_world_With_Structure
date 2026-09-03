# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, optional code intelligence, verification, review, repair, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## What is AER?

AER is the runtime/control-plane layer that governs how an AI coding agent moves from **intent to a verified engineering outcome**. The model is replaceable; AER owns the workflow, repository evidence, safety boundaries, verification, and proof.

```text
User intent / Jira / issue
          |
          v
       AER Control Plane
          |
   Intent -> Contract -> Repo Facts
          |
          v
    Adaptive workflow
          |
   +------+------+------+------+------+
   |      |      |      |      |      |
Research  POC   Debug Implement Review Grill
   |      |      |      |      |      |
   +------+------+------+------+------+
          |
          v
       Changeset
          |
          v
   Verify -> Review -> Proof
          |
          v
       Outcome
          |
          v
   Safe evaluation + learning
```

For substantial work, the durable artifact chain is:

`intent -> spec -> plan -> changeset -> verification -> review -> proof`

The broader engineering state is:

`INTENT -> CONTRACT -> REPO_FACTS -> DECISIONS -> EVIDENCE -> CHANGESET -> VERIFY -> OUTCOME -> OPEN_RISKS -> NEXT`

AER is therefore more than a prompt library or model wrapper. It is the control plane around the coding agent.

## GenAI coding system adaptation

AER now incorporates the most useful engineering ideas from the current `awesome-generative-ai-guide`: explicit context engineering, hybrid retrieval, adaptive planning, whole-system evaluation, independent verification, restrained multi-agent use, and production feedback. These are expressed as repository policies rather than dependencies on a specific model, framework, vector database, or agent host.

See `.ai-harness/GENAI_CODING_POLICY.md` and `docs/GENAI_CODING_ADAPTATION.md`.

## AER design principles

- Repository conventions before generic conventions.
- Human-written, non-obvious instructions before generated context inventories.
- Verification over model claims.
- Evidence before inference.
- Retrieve relevant evidence instead of replaying whole repositories, graphs, memories, or transcripts.
- Optimize verified outcome per total model call/token cost, not token count alone.
- Fresh-context verification for meaningful/high-risk changes when practical.
- Small independently verifiable work units for complex tasks.
- Session handoffs preserve durable state, not full transcripts.
- Focused entropy cleanup after substantial work without unrelated refactoring.
- Least privilege and isolated execution for risky work.
- Optional integrations, never mandatory dependencies.
- One adaptive runtime run by default; loops require explicit user intent.
- Progressive disclosure and targeted retrieval instead of full-repository prompting.
- Language and framework neutrality.
- New dependencies require an explicit decision and disclosure.
- Provider failure must degrade gracefully.
- Learned behavior must be evaluated before becoming executable policy.

## How AER fits with coding agents

```text
Claude / Codex / Gemini / compatible agent
                    |
                 Adapter
                    |
          AER Control Plane
                    |
       +------------+------------+
       |            |            |
     Policy       Context     Knowledge
       |            |            |
   risk/scope    retrieval    AST/graph/RAG
       |            |            |
       +------------+------------+
                    |
             Execute / Verify
                    |
              Review / Proof
```

The coding agent supplies model reasoning and tool interaction. AER supplies the repository-aware engineering process around it. Optional providers such as Graphify, code-mem, MCP servers, and compatible Agent Skills are capabilities discovered and selected when useful; they are not separate orchestration systems.

## Install for Claude Code

From Claude Code:

```text
/plugin marketplace add sourabhJainR/Hello_world_With_Structure
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

For local plugin development:

```text
/plugin marketplace add .
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

Or install on a developer box:

```bash
./install.sh
# or
python3 scripts/install_skill.py --auto
```

The installer detects supported agent environments and installs the skill with backups. It does not install third-party tools, modify MCP configuration, grant permissions, or silently change external integrations.

## Use it

Once installed, open any repository with Claude Code:

```bash
cd my-service
claude
```

Then use normal engineering language. You do not need to name the harness.

### Implement a Jira task

```text
Implement JIRA-4821. Add tenant-level export filtering, preserve backward compatibility, and add regression tests.
```

The orchestrator profiles the repository, finds existing filtering patterns, selects only relevant graph/search evidence, implements within local conventions, runs appropriate tests, and reviews the final diff.

### Investigate before changing code

```text
Investigate why the reporting API is intermittently timing out. Do not change code yet.
```

Expected behavior:

```text
Debug -> targeted graph/AST evidence -> relevant source -> history -> root-cause candidates -> evidence-backed findings
```

### Research

```text
Research the best two libraries for distributed locking for this repository. Recommend one and explain the trade-offs. Do not modify code.
```

Research is invoked because the task requests unknown/current information; implementation is not started automatically.

### POC

```text
Build a focused POC to determine whether this serializer can process 1M records within our latency target.
```

The POC workflow is selected only because feasibility is unresolved and an experiment is requested.

### Grill / review

```text
Grill this authentication change for security, compatibility, failure paths, and operational risk.
```

or:

```text
Review this caching change for correctness, performance, security, and regressions. Do not modify files.
```

### Fresh repository

```text
Build a small REST API for customer subscriptions.
```

If no local conventions exist, the orchestrator establishes a mature compatible structure, testing, logging, error handling, configuration, and dependency approach instead of pretending an existing pattern exists.

## Detailed usage and platform integration

For installation, Claude Code, Codex CLI, Gemini CLI, unsupported Agent Skills hosts, real-task examples, research/POC/review flows, Jira usage, troubleshooting, safe rollout, and the recommended golden path, see:

`docs/USAGE_AND_PLATFORM_INTEGRATION.md`

The short version is: install/discover the skill, open the target repository, describe the desired outcome and protected behavior, and let the orchestrator infer the minimum workflow. You should not need to know which internal skill, model, graph provider, memory provider, or retrieval strategy it selected.

## Optional intelligence extensions

The core works without extensions. When already installed, enabled, healthy enough, and relevant, the orchestrator can use:

- **Graphify** for AST and deterministic relationship/impact evidence.
- **code-mem / codebase-memory-mcp** for persistent code graph, semantic/structural search, call tracing, and impact analysis.
- **Superpowers** for TDD, planning, systematic debugging, and execution discipline.
- **Ponytail** for YAGNI and minimal-change pressure.
- **Caveman** for compact output/context handling.
- Other compatible Agent Skills and MCP servers discovered at runtime.

Extensions are capabilities, not dependencies. The orchestrator does not install or modify them without explicit approval. Provider output is bounded, ranked, deduplicated, and provenance-aware before entering model context.

## Context efficiency

The context strategy is inspired by the IO-efficiency idea behind FlashAttention: move less information through the expensive model boundary while retaining the information needed for correctness. It is not an implementation of FlashAttention.

Key rules:

1. Keep always-loaded instructions short and human-curated.
2. Retrieve rather than replay.
3. Rank and deduplicate evidence before prompt inclusion.
4. Budget context separately for discovery, planning, implementation, verification, and review.
5. Reuse stable evidence when the repository/provider state has not changed.
6. Use compact session handoffs instead of copying transcripts across contexts.
7. Prefer fresh verification context over giving the verifier the author's full reasoning.
8. Measure retries, tool calls, latency, cache usage, and verification failures alongside tokens.

See `docs/CONTEXT_EFFICIENCY.md`, `docs/CONTEXT_BUDGET.md`, `docs/SESSION_HANDOFF_AND_ENTROPY.md`, and `docs/VERIFICATION_INDEPENDENCE.md`.

## Engineering workflow disciplines

The orchestrator uses a composable, spec-driven workflow model rather than one large universal prompt:

`grill -> spec -> independently verifiable slices -> implement -> review`

That spine is adaptive:

- fuzzy/high-impact work starts with grilling and boundary clarification;
- settled small work can go directly to implementation;
- long-running work gets durable specification and handoff state;
- uncertain feasibility uses a disposable POC;
- hard bugs use reproduce/minimize/hypothesize/instrument/fix/regression-test;
- review checks both specification fidelity and repository engineering quality.

Detailed adaptation and licensing review:

`docs/AIHERO_SKILLS_ADAPTATION.md`

## Engineering operating-system model

The harness is designed as a portable software-engineering operating layer rather than a collection of prompts. For non-trivial work it maintains a compact Engineering State Ledger:

`INTENT -> CONTRACT -> REPO_FACTS -> DECISIONS -> EVIDENCE -> CHANGESET -> VERIFY -> OUTCOME -> OPEN_RISKS -> NEXT`

This lets work survive model, session, and host changes without replaying transcripts.

The ledger now records outcome separately from verification so future learning can distinguish “tests passed” from “the engineering change was accepted and successful.”

Before significant actions it uses lightweight gates:

`Understand -> Plan -> Change -> Proof -> Release`

The system also detects non-progressing retries and thrash. Repeated searches, edits, tests, or hypotheses that add no material evidence must stop and change strategy.

The user experience remains outcome-first: describe the goal naturally and the harness infers the workflow. For longer tasks it can expose concise checkpoints:

`UNDERSTOOD -> INVESTIGATING -> PLAN -> CHANGED -> PROVEN -> OUTCOME -> OPEN_RISKS`

See `docs/AGENT_OPERATING_SYSTEM_REVIEW.md` and `docs/P0_OPERATING_CONTRACT.md`.

## Reference applications

The repository contains isolated reference applications for exercising the orchestrator against ordinary software problems. They are examples only and are not dependencies of the core system.

Both examples use the same AER lifecycle and scenario vocabulary; the domain changes the guardrails, not the control plane. See `examples/README.md` for:

- `habit-tracker/` — low-risk CRUD, validation, streak logic, and regression tests.
- `family-financial-register/` — a higher-sensitivity fake-data, offline continuity register for assets, liabilities, documents, and responsible roles. It intentionally excludes credentials and recovery secrets.

The examples are deliberately kept outside `.ai-harness`, `state`, and runtime packages so the core remains domain-neutral. Their `HARNESS_SCENARIOS.md` files describe how the same AER contract is exercised without introducing example-specific orchestration logic.

## Evaluation

The repository contains dependency-free deterministic evals covering routing, unnecessary capability selection, policy invariants, skill metadata/context budgets, extension degradation, future readiness, and context-efficiency behaviors.

Run it with:

```bash
python scripts/run_evals.py
```

Run the complete tests with:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s examples/habit-tracker/tests -v
python -m unittest discover -s examples/family-financial-register/tests -v
```

Validate plugin packaging with:

```bash
python scripts/validate_plugin.py
```

Add a regression eval whenever a routing, context, extension, safety, verification, or skill-discovery defect is found. Provider-backed/model evals are optional and never required for core installation.

## Future-ready architecture

The core is intentionally separated from host agents and optional providers:

```text
                    Claude / Codex / Gemini / other agent
                                  |
                              adapter
                                  |
                    Adaptive AI Coding Orchestrator
                                  |
        +-------------------------+-------------------------+
        |                         |                         |
   Policy + routing         Knowledge fabric          Context engine
        |                         |                         |
   task/risk/state         AST / graph / RAG        bounded evidence
        |                         |                         |
        +-------------------------+-------------------------+
                                  |
                           Capability providers
                 /       |       |       |       \
            Graphify code-mem  optional skills  MCP providers
                                  |
                                  v
                       Execute -> Verify -> Review
                                  |
                         Evaluation + learning
```

Provider contracts, state semantics and future maturity gates are documented in `docs/FUTURE_ARCHITECTURE.md`, `docs/AGENT_COMPATIBILITY.md`, and `docs/EXTENSION_CONTRACT.md`.

## Evaluation maturity

The project uses three layers:

1. **Fast deterministic evals** on every change for routing, metadata, context and safety invariants.
2. **Regression evals** for previously observed failures and extension-degradation cases.
3. **Provider/model evals** for quality, latency, tool calls and cost when a real model/provider is available.

A model-generated improvement does not become an executable default merely because it scored well once. Changes require reproducible evidence and regression coverage.

## Productization and IP

The practical commercial path is to keep the local developer experience easy to adopt while monetizing organization-level value: hosted evaluation, private engineering memory, regression intelligence, enterprise policy controls, fleet analytics, premium integrations, and rollout/support.

Do not depend on obfuscation or client-side anti-copy mechanisms. The repository is public, so the durable moat should be the accumulated evidence and outcome loop:

`Repository evidence -> Outcome data -> Evaluation corpus -> Learned engineering patterns -> Better routing/retrieval/verification -> Better outcomes`

The public repository currently has no detected software license. Choose the intended legal licensing model before commercial distribution rather than silently imposing one through automation. See `IP_AND_COMMERCIALIZATION.md` and `SECURITY.md`.

For product claims, measure real repositories against the team's normal coding-agent workflow using accepted-change rate, time to accepted change, escaped regressions, RCA precision, review effort, tool/model calls, token cost, latency, and rework.

## Safety

The orchestrator never silently installs tools, changes permissions, connects to production, merges changes, or promotes learned behavior into executable policy. Repository and organization instructions remain authoritative. Cancellation, provider failure, partial execution, and successful completion must remain distinguishable.

## Development

The project is intentionally dependency-light. Optional third-party integrations are documented in `.ai-harness/DEPENDENCIES.md` and are not required for core operation.
