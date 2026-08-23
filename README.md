# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## Adaptive AI Coding System

This repository includes a provider-neutral AI coding orchestrator designed to sit above Claude Code, Codex, Gemini CLI, local agents, or another compatible AI CLI.

The agent infers the required state from a prompt, task, Jira item, issue, repository context, risk, and uncertainty. Developers normally do not need to select a workflow manually.

```text
Input
  -> State + Intent + Risk + Uncertainty
  -> Relevant Memory
  -> Token-aware Context
  -> Minimum Safe Capabilities
  -> Execute
  -> Validate
  -> Diff / Verification Gate
  -> Review / Grill when justified
  -> Learn
  -> Groom memory
```

### Examples

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

## Skills

The canonical auto-invokable AgentSkill is:

`.agents/skills/ai-coding-orchestrator/SKILL.md`

Claude also has a native entry point under `.claude/skills/ai-coding-orchestrator/`.

The repository-wide instruction surface is `AGENTS.md`.

## Engineering principles

The orchestrator applies language-neutral engineering principles from `.ai-harness/principles.md`, including DRY, YAGNI, KISS, dependency inversion, selective SOLID, cohesion/coupling, security by default, failure awareness, observability, reversibility, compatibility, behavior-focused testing, least privilege, and evidence over assumption.

## Learning and evolution

The system records compact observations and candidate patterns under `.ai-harness/memory/`.

Learning is governed:

- one run can create an observation, not a permanent rule
- repeated successful observations increase confidence
- grooming consolidates duplicates and promotes trusted patterns
- harness code, provider permissions, security policy, and permanent rules are not self-modified from model output

## Token and context engineering

The harness uses a compact repository map, relevance-ranked memory, bounded phase history, stable instructions, and explicit context budgets. It aims to spend tokens on the files and decisions that matter rather than replaying whole transcripts.

## Recovery and verification

Runs persist checkpoints and phase artifacts. Provider failures and verification failures have bounded repair paths. Validation uses explicit argv commands or safe auto-discovery; shell parsing is avoided for configured validation commands. Completion also performs a final `git diff --check` gate.

## Providers

Providers are configured in `.ai-harness/config.toml`. The bridge supports a `{python}` placeholder so the same configuration works across environments where the Python executable name differs.

## Regression evaluation

Representative routing cases live in `.ai-harness/evals/cases.jsonl`. Changes to routing logic should keep `python .ai-harness/run.py eval` passing before promotion.

See `.ai-harness/README.md` for the detailed architecture and operating model.
