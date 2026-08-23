# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## Adaptive AI Coding System

This repository includes a provider-neutral AI coding orchestrator designed to sit above Claude Code, Codex, Gemini CLI, local agents, or another compatible AI CLI.

The agent should infer the required state from a prompt, task, Jira item, issue, or repository context. Developers do not normally need to select a workflow manually.

```text
Input
  -> State + Intent + Risk + Uncertainty
  -> Relevant Memory
  -> Token-aware Context
  -> Minimum Safe Capabilities
  -> Execute
  -> Validate
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

# Research only
python .ai-harness/run.py run --task "Compare Redis and Valkey for this service"

# Feasibility / POC
python .ai-harness/run.py run --task "Can this workload be moved to WebAssembly?"

# Inspect learned knowledge
python .ai-harness/run.py memory
python .ai-harness/run.py groom
```

## Skills

The canonical auto-invokable AgentSkill is:

`.agents/skills/ai-coding-orchestrator/SKILL.md`

Claude also has a native entry point under `.claude/skills/ai-coding-orchestrator/`.

The repository-wide instruction surface is `AGENTS.md`.

## Learning and evolution

The system records compact observations and candidate patterns under `.ai-harness/memory/`.

Learning is governed:

- one run can create an observation, not a permanent rule
- repeated successful observations increase confidence
- grooming consolidates duplicates and promotes trusted patterns
- harness code and permanent agent rules are not self-modified from model output

This gives the agent a continuous learning loop without allowing a single bad response to corrupt the orchestration layer.

## Token optimization

The harness uses a compact repository map, relevance-ranked memory, bounded phase history, and explicit context budgets. The goal is to spend tokens on the files and decisions that matter rather than replaying entire transcripts.

## Providers

Providers are configured in `.ai-harness/config.toml`. The default bridge appends the generated prompt as the final argument to the selected CLI, while custom provider commands can be added using the same pattern.

## Validation

Project-specific commands belong in `[validation]` in `.ai-harness/config.toml`. The harness records validation evidence and does not report success without observed results.

See `.ai-harness/README.md` for the architecture and operating model.