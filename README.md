# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## Adaptive AI Coding System

This repository includes a provider-neutral AI coding orchestrator designed to sit above Claude Code, Codex, Gemini CLI, local agents, or another compatible AI CLI.

The deployable skill can be installed globally so it is available when working in any repository. The normal runtime is one adaptive run per task; recursive execution is never automatic.

```text
Input
  -> Repository profile + extension discovery
  -> State + Intent + Risk + Uncertainty
  -> Graph / AST / exact / semantic evidence
  -> Flash-style bounded context
  -> Minimum Safe Capabilities
  -> Execute
  -> Validate
  -> Diff / Verification Gate
  -> Review / Grill when justified
  -> Learn
```

## Deploy the skill

For a detected local coding-agent environment:

```bash
python scripts/install_skill.py --auto
```

For explicit global installation across Claude Code, generic Agent Skills, and Gemini:

```bash
python scripts/install_skill.py --global
```

The installer is idempotent and backup-aware. It does not install third-party tools, change MCP configuration, grant permissions, or overwrite user instructions without a backup. Restart the coding agent after installation.

The canonical deployable skill is:

`skills/ai-coding-orchestrator/SKILL.md`

The Claude plugin manifest is:

`.claude-plugin/plugin.json`

See `docs/DEPLOYMENT.md` for project-scoped and provider-specific setup.

## Optional extensions

The orchestrator uses optional extensions when already installed and enabled. None are mandatory:

- Graphify: AST/knowledge graph and relationship/impact evidence.
- code-mem / codebase-memory-mcp: persistent code graph, semantic search, call tracing and impact analysis.
- Superpowers: brainstorming, TDD, systematic debugging, planning and execution skills.
- Ponytail: YAGNI/minimal-change discipline.
- Caveman: compact communication and token-efficient subagent output.
- Other Agent Skills and MCP servers: task-specific capabilities.

Availability is detected without installation or mutation:

```bash
python .ai-harness/extension_registry.py
```

Extension conflict precedence is repository instructions, security/permissions, acceptance criteria, local architecture, verification, orchestrator, extension guidance, then model preference.

## Examples

```bash
# Adaptive coding task
python .ai-harness/run.py run --task "Add validation to the export flow"

# Jira task
python .ai-harness/run.py run --jira PROJ-1827 --task "Implement the requested change"

# Jira content from a local export
python .ai-harness/run.py run --jira-file ./jira/PROJ-1827.txt

# Research, debugging, POC and review are inferred automatically
python .ai-harness/run.py run --task "Compare Redis and Valkey for this service"
python .ai-harness/run.py run --task "Investigate the intermittent export timeout"
python .ai-harness/run.py run --task "Can this workload be moved to WebAssembly?"

# Inspect learned knowledge and routing quality
python .ai-harness/run.py memory
python .ai-harness/run.py groom
python .ai-harness/run.py eval

# Resume an interrupted run from its checkpoint
python .ai-harness/run.py run --task "..." --resume .ai-harness/runs/<run-id>
```

## Engineering principles

The orchestrator applies language-neutral engineering principles from `.ai-harness/principles.md`, including DRY, YAGNI, KISS, dependency inversion, selective SOLID, cohesion/coupling, security by default, failure awareness, observability, reversibility, compatibility, behavior-focused testing, least privilege, and evidence over assumption.

## Repository-first coding style

New interfaces, classes, constants, services, adapters, tests, and other files must follow the existing repository's segregation, naming and coding style. When multiple local patterns exist, the orchestrator selects the most mature compatible and scalable pattern. Only when no local convention exists does it fall back to a current mature ecosystem convention.

## Learning and evolution

The system records compact observations and candidate patterns under `.ai-harness/memory/`.

Learning is governed:

- one run can create an observation, not a permanent rule
- repeated successful observations increase confidence
- grooming consolidates duplicates and promotes trusted patterns
- harness code, provider permissions, security policy, and permanent rules are not self-modified from model output

## Token and context engineering

The harness uses structural retrieval, relevance ranking, stable context, bounded evidence, tiled context, compact history and explicit context budgets. The FlashAttention reference is an IO/context-engineering principle, not a dependency on the FlashAttention library.

## Recovery and verification

Runs persist checkpoints and phase artifacts. Provider failures and verification failures have bounded repair paths. Validation uses explicit argv commands or safe auto-discovery; shell parsing is avoided for configured validation commands. Completion also performs a final `git diff --check` gate.

## Providers

Providers are configured in `.ai-harness/config.toml`. The bridge supports a `{python}` placeholder so the same configuration works across environments where the Python executable name differs.

## Regression evaluation

Representative routing cases live in `.ai-harness/evals/cases.jsonl`. Changes to routing logic should keep `python .ai-harness/run.py eval` passing before promotion.

See `.ai-harness/README.md` and `docs/DEPLOYMENT.md` for the detailed architecture and operating model.
