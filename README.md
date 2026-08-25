# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. It turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, optional code intelligence, verification, review, repair, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## What it does

```text
User task / Jira / issue
        |
        v
Repository rules + session state
        |
        v
Task classification + risk
        |
        v
Optional capability discovery
        |
        v
AST / graph / exact / semantic evidence
        |
        v
Bounded context and adaptive workflow
        |
        +--> research
        +--> POC
        +--> debug
        +--> implement
        +--> review / grill
        |
        v
Repository-native verification
        |
        v
Independent review -> repair when needed
        |
        v
Evidence-backed completion
        |
        v
Evaluation + safe learning signals
```

## Design principles

- Repository conventions before generic conventions.
- Verification over model claims.
- Evidence before inference.
- Least privilege and isolated execution for risky work.
- Optional integrations, never mandatory dependencies.
- One adaptive runtime run by default; loops require explicit user intent.
- Progressive disclosure and targeted retrieval instead of full-repository prompting.
- Language and framework neutrality.
- New dependencies require an explicit decision and disclosure.
- Provider failure must degrade gracefully.
- Learned behavior must be evaluated before becoming executable policy.

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

The orchestrator profiles the repository, finds existing filtering patterns, selects relevant graph/search evidence, implements within local conventions, runs appropriate tests, and reviews the final diff.

### Investigate before changing code

```text
Investigate why the reporting API is intermittently timing out. Do not change code yet.
```

Expected behavior:

```text
Debug -> graph/AST evidence -> relevant source -> history -> root-cause candidates -> evidence-backed findings
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

## Optional intelligence extensions

The core works without extensions. When already installed, enabled, healthy enough, and relevant, the orchestrator can use:

- **Graphify** for AST and deterministic relationship/impact evidence.
- **code-mem / codebase-memory-mcp** for persistent code graph, semantic/structural search, call tracing, and impact analysis.
- **Superpowers** for TDD, planning, systematic debugging, and execution discipline.
- **Ponytail** for YAGNI and minimal-change pressure.
- **Caveman** for compact output/context handling.
- Other compatible Agent Skills and MCP servers discovered at runtime.

Extensions are capabilities, not dependencies. The orchestrator does not install or modify them without explicit approval. Provider output is bounded and ranked before entering model context.

## Context efficiency

The context engine uses a FlashAttention-inspired IO strategy: keep stable instructions small, retrieve evidence in bounded tiles, rank before inclusion, reuse stable context, deduplicate overlap, and preserve verification evidence losslessly.

Detailed operating guidance is loaded progressively from `skills/ai-coding-orchestrator/references/` rather than putting the entire policy set into every model prompt.

See `docs/CONTEXT_BUDGET.md` and `docs/EXTENSION_CONTRACT.md` for the governing rules.

## Evaluation

The repository contains a dependency-free deterministic eval suite covering routing, unnecessary capability selection, policy invariants, skill metadata/context budgets, extension degradation, and future-readiness cases.

Run it with:

```bash
python scripts/run_evals.py
```

Run the complete tests with:

```bash
python -m unittest discover -s tests -v
```

Validate plugin packaging with:

```bash
python scripts/validate_plugin.py
```

Add a regression eval whenever a routing, context, extension, safety, or skill-discovery defect is found. Provider-backed/model evals are optional and never required for core installation.

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
                 /          |          |          \
            Graphify    code-mem  Superpowers  other MCP/skills
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

## Safety

The orchestrator never silently installs tools, changes permissions, connects to production, merges changes, or promotes learned behavior into executable policy. Repository and organization instructions remain authoritative. Cancellation, provider failure and partial execution must remain distinguishable from successful completion.

## Development

The project is intentionally dependency-light. Optional third-party integrations are documented in `.ai-harness/DEPENDENCIES.md` and are not required for core operation.
