# Hello World With Structure

Interactive learning platform with code execution, history tracking, and snippet management across multiple programming languages.

## AI Coding Harness

This repository includes a generic, provider-neutral harness under `.ai-harness/`.

It can orchestrate coding workflows using any compatible AI CLI, including Claude Code, Codex, Gemini CLI, local agents, or a custom wrapper.

### Default workflow

```text
Understand -> Plan -> Implement -> Review -> Fix -> Validate
```

### On-demand capabilities

These are optional and only run when explicitly requested:

```text
Research  - investigate technology, documentation, alternatives, and evidence
POC       - test technical feasibility with a focused experiment
Grill     - adversarially challenge assumptions, risks, edge cases, and design choices
```

Capabilities can be used alone or composed with a coding workflow.

```bash
# Normal coding
python .ai-harness/run.py run --agent claude --task "Describe the change"

# Research before implementation
python .ai-harness/run.py run --agent claude --task "Describe the change" --capability research

# Research + POC + coding
python .ai-harness/run.py run --agent claude --task "Describe the change" --capability research --capability poc

# Challenge an approach
python .ai-harness/run.py run --agent claude --workflow grill --task "Challenge this design"
```

List providers and workflows:

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py workflows
```

To use another CLI, add its command to `.ai-harness/config.toml`.

See `.ai-harness/README.md` for configuration and usage details.
