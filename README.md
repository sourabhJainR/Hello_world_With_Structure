# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## AI Coding Harness

This repository now includes a generic, provider-neutral harness under `.ai-harness/`.

It can orchestrate coding workflows using any compatible AI CLI, including Claude Code, Codex, Gemini CLI, local agents, or a custom wrapper.

### Workflow

```text
Understand -> Plan -> Implement -> Review -> Fix -> Validate
```

### Quick start

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py run --agent claude --task "Describe the change you want"
```

To use another CLI, add its command to `.ai-harness/config.toml`.

See `.ai-harness/README.md` for the full configuration and design.
