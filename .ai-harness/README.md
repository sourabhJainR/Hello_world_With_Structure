# AI Coding Harness

A lightweight, provider-neutral orchestration layer for Claude Code, Codex, Gemini CLI, local agents, and custom AI coding CLIs.

The design uses proven patterns from mature coding-agent projects without importing their full frameworks: repository maps for focused context, durable repository instructions, reusable skills, explicit workflows, session artifacts, and validation feedback loops.

## Layout

```text
.ai-harness/
  config.toml
  run.py
  README.md
  skills/
    research/SKILL.md
    poc/SKILL.md
    grill/SKILL.md
  prompts/
    system.md
    phases/
      understand.md
      plan.md
      research.md
      poc.md
      implement.md
      grill.md
      review.md
      fix.md
  runs/                    # generated session artifacts; ignored by git
```

The repository root also contains `AGENTS.md` as the shared instruction surface, plus lightweight `CLAUDE.md` and `GEMINI.md` entry points.

## Core model

The harness separates four concerns:

1. **Provider** — how an AI CLI is launched.
2. **Workflow** — which phases run and in what order.
3. **Capability** — optional research, POC, or adversarial review behavior.
4. **Evidence** — prompts, outputs, repository map, validation logs, and git state captured for each run.

Changing the AI provider does not change the workflow.

## Workflows

```text
coding           understand -> plan -> implement -> review -> fix
research         research
poc              understand -> research -> poc
grill            grill
research-coding  research -> understand -> plan -> implement -> review -> fix
```

## Optional capabilities

Capabilities are opt-in and can be composed.

### Research

Use when the task depends on external facts, unknown technology, competing approaches, or architecture decisions.

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Compare Redis and PostgreSQL for distributed locking" \
  --capability research
```

### POC

Use when feasibility is the main question.

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Validate whether this workload can run efficiently with WebAssembly" \
  --workflow poc
```

### Grill

Use when you want a deliberate adversarial challenge before approving a design or implementation.

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Challenge this multi-tenant authorization design" \
  --workflow grill
```

### Compose capabilities

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Introduce distributed caching for the reporting service" \
  --capability research \
  --capability poc \
  --capability grill
```

When a coding workflow is used, optional capabilities are inserted before implementation.

## Automatic routing

Use `--auto` to infer likely optional capabilities from the task wording:

```bash
python .ai-harness/run.py run \
  --agent claude \
  --task "Evaluate and compare approaches for adding OAuth authentication" \
  --auto
```

Automatic routing is intentionally conservative. Explicit `--workflow` and `--capability` choices take precedence.

## Repository context

Generate a compact repository map with:

```bash
python .ai-harness/run.py context
```

Every run also gets its own repository map. It contains file paths and common class/function symbols where they can be detected without third-party parsers.

## Run artifacts

Every execution gets a unique session directory:

```text
.ai-harness/runs/<timestamp>/
  manifest.json
  task.txt
  repository-map.md
  <phase>.prompt.md
  <phase>.output.md
  validation-*.log
  git-state-final.txt
  grill-action-required.md       # only when grill blocks approval
```

This provides a handoff record between phases and makes runs inspectable.

## Provider configuration

Providers are configured as argument arrays, not shell strings:

```toml
[providers.my-agent]
command = ["my-agent", "--prompt-file", "{prompt_file}"]
working_directory = "{workspace}"
```

Available placeholders:

- `{prompt_file}`
- `{workspace}`
- `{phase}`
- `{run_dir}`

The same workflow can therefore call Claude, Codex, Gemini, or another CLI without changing the harness logic.

## Commands

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py workflows
python .ai-harness/run.py capabilities
python .ai-harness/run.py context
python .ai-harness/run.py run --agent claude --task "..."
python .ai-harness/run.py run --agent claude --task "..." --workflow research
python .ai-harness/run.py run --agent claude --task "..." --capability research --capability grill
python .ai-harness/run.py run --agent claude --task "..." --auto
python .ai-harness/run.py run --agent claude --task "..." --dry-run
```

## Validation

Project-specific commands can be placed in `config.toml` under `[validation]`. They run after implementation and fixes. The harness does not assume .NET, Node, Python, Java, or another stack.

## Safety and boundaries

The harness does not grant additional permissions to an AI CLI. The selected provider remains responsible for its own sandbox, approvals, network policy, and tool permissions.

Research and grill are read-only by contract. POC should stay isolated and clearly labelled as experimental. Production implementation belongs in the implementation phase.

For unattended runs, use a dedicated branch or worktree, least-privileged credentials, explicit validation, and a provider sandbox where available.
