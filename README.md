# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. It turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, optional code intelligence, verification, review, repair, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## What it does

```text
User task / Jira / issue
        |
        v
Repository rules + state
        |
        v
Optional extension discovery
        |
        v
AST / graph / exact / semantic evidence
        |
        v
Bounded context and task routing
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
Evidence-backed completion and learning
```

Core principles:

- Repository conventions before generic conventions.
- Verification over model claims.
- Least privilege and isolated execution for risky work.
- Optional integrations, never mandatory dependencies.
- One adaptive runtime run by default; loops require explicit user intent.
- Progressive disclosure and targeted retrieval instead of full-repository prompting.
- Language and framework neutrality.
- New dependencies require an explicit decision and disclosure.

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

The core works without extensions. When already installed, enabled, and relevant, the orchestrator can use:

- **Graphify** for AST and deterministic relationship/impact evidence.
- **code-mem / codebase-memory-mcp** for persistent code graph, semantic/structural search, call tracing, and impact analysis.
- **Superpowers** for TDD, planning, systematic debugging, and execution discipline.
- **Ponytail** for YAGNI and minimal-change pressure.
- **Caveman** for compact output/context handling.
- Other compatible Agent Skills and MCP servers discovered at runtime.

Extensions are capabilities, not dependencies. The orchestrator does not install or modify them without explicit approval and avoids duplicate queries when providers return the same evidence.

## Context efficiency

The context engine uses a FlashAttention-inspired IO strategy: keep stable instructions small, retrieve evidence in bounded tiles, rank before inclusion, reuse stable context, and preserve verification evidence losslessly.

Detailed operating guidance is loaded progressively from `skills/ai-coding-orchestrator/references/` rather than putting the entire policy set into every model prompt.

## Evaluation

The repository contains a dependency-free deterministic eval suite covering routing, unnecessary capability selection, policy invariants, and skill metadata/context budgets.

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

## Architecture

```text
                     AI Coding Orchestrator
                              |
          +-------------------+-------------------+
          |                   |                   |
       Core engine        Knowledge fabric     Context engine
          |                   |                   |
       routing           AST / graph / RAG    bounded evidence
          |                   |                   |
          +-------------------+-------------------+
                              |
                       Optional extensions
                  /          |          |          \
             Graphify    code-mem  Superpowers  other MCP/skills
                              |
                              v
                    Execute -> Verify -> Review
                              |
                           Learn
```

See:

- `docs/PLUGIN_ARCHITECTURE.md` for plugin boundaries.
- `docs/MARKETPLACE.md` for distribution.
- `docs/DEPLOYMENT.md` for developer-machine deployment.
- `.ai-harness/evals/EVAL_POLICY.md` for evaluation governance.
- `skills/ai-coding-orchestrator/references/` for progressive-disclosure guidance.

## Safety

The orchestrator never silently installs tools, changes permissions, connects to production, merges changes, or promotes learned behavior into executable policy. Repository and organization instructions remain authoritative.

## Development

The project is intentionally dependency-light. Optional third-party integrations are documented in `.ai-harness/DEPENDENCIES.md` and are not required for core operation.
