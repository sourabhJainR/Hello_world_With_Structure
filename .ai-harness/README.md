# AI Coding Harness

A provider-neutral coding harness for running Claude Code, Codex, Gemini CLI, local agents, or other AI coding CLIs through the same repository workflow.

## Goals

- Keep AI-provider commands separate from the coding workflow.
- Give every agent the same repository context, rules, and acceptance criteria.
- Capture plans, implementation output, review findings, diffs, and validation results.
- Make runs reproducible and easy to inspect.
- Support optional research, POC, and adversarial challenge without forcing them into every task.
- Avoid requiring a framework-specific SDK.

## Layout

```text
.ai-harness/
  config.toml
  run.py
  prompts/
    system.md
    phases/
      understand.md
      plan.md
      implement.md
      review.md
      fix.md
      research.md
      poc.md
      grill.md
  runs/
```

## Core coding workflow

```text
Understand -> Plan -> Implement -> Review -> Fix -> Validate
```

This is the default workflow. Optional capabilities are invoked only when requested.

## Optional capabilities

### Research

Use when a task depends on unknown technology, library behavior, standards, external documentation, alternatives, or a decision that needs evidence.

```bash
python .ai-harness/run.py run \
  --agent claude \
  --workflow research \
  --task "Compare authentication approaches for this application"
```

Or add research before a normal coding run:

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Add OAuth login" \
  --capability research
```

### POC

Use when the main risk is technical feasibility rather than implementation effort. A POC should test a hypothesis and return evidence, not silently become production code.

```bash
python .ai-harness/run.py run \
  --agent codex \
  --workflow poc \
  --task "Determine whether offline sync can work with the current architecture"
```

Or compose it with coding:

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Add streaming support" \
  --capability research \
  --capability poc
```

### Grill

Use when you want an adversarial technical challenge before accepting a design or implementation. Grill is read-only and questions assumptions, failure modes, security, scale, tests, rollback, and simpler alternatives.

```bash
python .ai-harness/run.py run \
  --agent gemini \
  --workflow grill \
  --task "Challenge the proposed caching architecture"
```

Or add it to a coding run:

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Implement multi-tenant authorization" \
  --capability grill
```

Capabilities can be repeated and are composed in the order supplied. When implementation exists, requested capabilities run before `implement`.

## Included workflows

```text
coding           understand -> plan -> implement -> review -> fix
research         research
poc              understand -> research -> poc
grill            grill
research-coding  research -> understand -> plan -> implement -> review -> fix
```

List configured workflows:

```bash
python .ai-harness/run.py workflows
```

## Quick start

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py run --agent claude --task "Add input validation"
```

Dry run without invoking an AI CLI:

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Add input validation" \
  --capability research \
  --capability grill \
  --dry-run
```

The harness creates a timestamped run under `.ai-harness/runs/`. Each run stores the generated prompts, provider output, metadata, validation logs, and final git state.

## Configure another AI CLI

Edit `.ai-harness/config.toml` and add a provider. The command is an argument array, not a shell string, so provider execution does not invoke a shell.

Supported placeholders inside command arguments:

- `{prompt_file}` - absolute path to the generated phase prompt
- `{workspace}` - repository root
- `{phase}` - current phase or capability name

Example:

```toml
[providers.my-agent]
command = ["my-agent", "--prompt-file", "{prompt_file}"]
working_directory = "{workspace}"
```

## Validation

Optional validation commands can be configured in `config.toml`. They run after implementation and after fixes. Keep commands project-specific; the harness does not assume .NET, Node, Python, or any other stack.

## Safety model

The harness does not grant extra permissions to an AI CLI. The selected AI tool still controls what it can do. The harness orchestrates prompts and captures outputs.

For unattended CI usage, prefer a restricted service account, a clean working tree, explicit validation commands, and a dedicated branch or worktree.
