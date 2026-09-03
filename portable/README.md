# AER Portable Bundle

The portable distribution is designed to move the current AER engineering control plane between machines and repositories without turning each target repository into a fork of the AER project.

## What is carried

The bundle contains the complete provider-neutral `.ai-harness` implementation plus the canonical `ai-coding-orchestrator` Agent Skill. This includes the current routing/context policies, context cache, learning engine and controller, policy registry, rollback controls, regression corpus, shadow/canary evaluation, verification controls, extension contracts, and supporting runtime modules present in the source `.ai-harness` tree.

Mutable or machine-specific state is deliberately excluded: execution journals, telemetry, task-memory/regression event logs, worktrees, and Python caches. A target repository creates its own state after installation.

## Build an offline bundle

Run from the AER source repository:

```bash
python portable/aer.py build --output aer-portable.zip
python portable/aer.py verify aer-portable.zip
```

The ZIP is content-addressed by a manifest and can be copied to another machine with no Git access required.

## Install into any repository

On the target machine:

```bash
python aer.py install aer-portable.zip /path/to/target-repo
```

By default the generic Agent Skill is installed under `~/.agents/skills`. Use `--skill claude`, `--skill gemini`, `--skill all`, or `--skill none` when a different host layout is desired.

The installer backs up an existing `.ai-harness` before replacing it and never changes git configuration, credentials, MCP configuration, permissions, production access, or merge authority.

## Portability contract

A target repository only needs Python 3.11+ to unpack and install the bundle. The core remains dependency-light and provider-neutral. Claude, Codex, Gemini, MCP servers, Graphify, code-mem, and other tools remain optional capabilities selected by the installed harness rather than dependencies of the bundle.

The bundle is the distribution unit; the target repository owns its repository-specific instructions, source code, tests, configuration, and learned state.

## Lifecycle after installation

```text
intent
  -> route/context
  -> execute/verify/review
  -> observe outcome
  -> learn candidate
  -> deterministic regression replay
  -> shadow evaluation
  -> bounded canary
  -> explicit promotion
  -> monitor
  -> rollback when health degrades
```

Learning stays advisory and safety-critical controls remain authoritative.
