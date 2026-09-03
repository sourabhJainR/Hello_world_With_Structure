# AER Portable Bundle

The portable distribution is **repository-isolated by design**. AER is installed under the user's machine-level `~/.aer` directory and the selected Agent Skill is installed in a user-level skill location. A target project is a workspace only; the installer does not vendor AER files into that project.

## What is carried

The bundle contains the complete provider-neutral `.ai-harness` implementation plus the canonical `ai-coding-orchestrator` Agent Skill. This includes the current routing/context policies, context cache, learning engine and controller, policy registry, rollback controls, regression corpus, shadow/canary evaluation, verification controls, extension contracts, and supporting runtime modules present in the source `.ai-harness` tree.

Mutable or machine-specific state is excluded from the bundle: execution journals, telemetry, task-memory/regression event logs, worktrees, and Python caches.

## Build an offline bundle

Run from the AER source repository:

```bash
python portable/aer.py build --output aer-portable.zip
python portable/aer.py verify aer-portable.zip
```

The ZIP is content-addressed by a manifest and can be copied to another machine with no Git access required.

## Install on a machine

```bash
python aer.py install aer-portable.zip
```

The installer writes only to user-scoped AER/Agent-Skill locations such as `~/.aer` and `~/.agents/skills`. It accepts no target-repository path because installation must not mutate a project.

Use `--skill claude`, `--skill gemini`, `--skill all`, or `--skill none` for host selection.

## Repository isolation contract

These are hard guarantees of the portable installer:

- It does **not** create `.ai-harness` in a target repository.
- It does **not** replace, delete, or back up existing target files.
- It does **not** add files to the target Git working tree or index.
- It does **not** modify `.git/config`, hooks, remotes, branches, or ignore files.
- It does **not** modify MCP configuration, credentials, permissions, production access, or merge authority.
- A repository that was clean before AER installation remains unchanged after AER installation.

Project-specific instructions remain owned by the project. AER implementation, configuration, caches, journals, learned state, regression corpus, and runtime code remain outside the project.

## Using AER with any repository

After machine-level installation, open any repository with the supported coding agent and use the normal AER skill. The skill treats the current repository as the workspace and keeps the AER implementation outside it. Optional integrations remain opt-in and are never installed automatically.

AER may inspect the repository, run repository-native commands and change project files only when the user's engineering task requires those changes. Those are the user's requested product/code changes, not AER installation artifacts.

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

Learned behavior remains advisory and safety-critical controls remain authoritative.
