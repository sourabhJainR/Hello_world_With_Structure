# AI Coding Harness

A provider-neutral coding harness for running Claude Code, Codex, Gemini CLI, local agents, or other AI coding CLIs through the same repository workflow.

## Goals

- Keep AI-provider commands separate from the coding workflow.
- Give every agent the same repository context, rules, and acceptance criteria.
- Capture plans, implementation output, review findings, diffs, and validation results.
- Make runs reproducible and easy to inspect.
- Avoid requiring a framework-specific SDK.

## Layout

```text
.ai-harness/
  config.toml                 # providers, workflow, validation commands
  run.py                      # cross-platform harness CLI
  prompts/
    system.md                 # repository-wide AI instructions
    phases/
      understand.md
      plan.md
      implement.md
      review.md
      fix.md
  runs/                       # generated run artifacts; ignored by git
```

## Quick start

From the repository root:

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py run --agent claude --task "Add input validation to the sample API"
```

The harness creates a timestamped run under `.ai-harness/runs/` and executes the configured phases.

## Configure another AI CLI

Edit `.ai-harness/config.toml` and add a provider. The command is an argument array, not a shell string, so the harness does not invoke a shell for provider execution.

Supported placeholders inside command arguments:

- `{prompt_file}` - absolute path to the generated phase prompt
- `{workspace}` - repository root
- `{phase}` - current phase name

Example:

```toml
[providers.my-agent]
command = ["my-agent", "--prompt-file", "{prompt_file}"]
working_directory = "{workspace}"
```

This keeps the workflow independent of the provider CLI.

## Workflow

The default workflow is:

```text
understand -> plan -> implement -> review -> fix
```

The fix phase only runs when the review output contains a configurable failure marker.

Each phase receives:

- repository instructions
- the user task
- current git state
- relevant previous phase output
- phase-specific instructions

## Validation

Optional validation commands can be configured in `config.toml`. They run after implementation and after fixes. Keep commands project-specific; the harness does not assume .NET, Node, Python, or any other stack.

## Safety model

The harness does not grant extra permissions to an AI CLI. The selected AI tool still controls what it can do. The harness only orchestrates prompts and captures outputs.

For unattended CI usage, prefer a restricted service account, a clean working tree, explicit validation commands, and a dedicated branch/worktree.
