# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## AI Coding Harness

This repository includes a generic, provider-neutral AI coding harness under `.ai-harness/`.

It can orchestrate Claude Code, Codex, Gemini CLI, local agents, or a custom AI CLI through the same workflow and evidence model.

### Default coding workflow

```text
Understand -> Plan -> Implement -> Review -> Fix -> Validate
```

### On-demand capabilities

```text
Research  - investigate technology, documentation, alternatives, and evidence
POC       - test technical feasibility with a focused experiment
Grill     - adversarially challenge assumptions, risks, edge cases, and design choices
```

Capabilities are optional and can be composed with normal coding.

```bash
# Normal coding
python .ai-harness/run.py run --agent claude --task "Describe the change"

# Research before implementation
python .ai-harness/run.py run --agent claude --task "Describe the change" --capability research

# Research + POC + Grill + coding
python .ai-harness/run.py run --agent claude --task "Describe the change" --capability research --capability poc --capability grill

# Let the harness suggest optional capabilities
python .ai-harness/run.py run --agent claude --task "Evaluate approaches for OAuth authentication" --auto

# Run only a research workflow
python .ai-harness/run.py run --agent claude --workflow research --task "Compare authentication approaches"

# Challenge a design
python .ai-harness/run.py run --agent claude --workflow grill --task "Challenge this design"
```

### Context and inspection

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py workflows
python .ai-harness/run.py capabilities
python .ai-harness/run.py context
```

Every run captures a repository map, phase prompts, agent outputs, metadata, validation logs, and final git state under `.ai-harness/runs/`.

The repository also provides shared AI instructions through `AGENTS.md`, with provider-specific entry points in `CLAUDE.md` and `GEMINI.md`.

To use another AI CLI, add its argument-array command to `.ai-harness/config.toml`.

See `.ai-harness/README.md` for the full architecture, workflows, capabilities, provider configuration, and safety model.
