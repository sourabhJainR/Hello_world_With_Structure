# AER Portable Distribution

AER is a **machine-scoped, repository-isolated, version-pinned engineering control plane**. Installing, updating, or rolling back AER never vendors its implementation into the repository being worked on.

## Distribution unit

The bundle contains the current provider-neutral AER runtime and canonical Agent Skill, including routing, bounded context, context cache, learning, policy registry, rollback controls, regression corpus, shadow/canary evaluation, verification, capability planning, and optional-extension contracts.

Mutable machine/session state is excluded from the bundle: execution journals, telemetry, learned task logs, worktrees, caches, and Python caches.

## Install

```bash
python aer_cli.py install aer-portable.zip
```

AER is installed under `~/.aer/versions/v<version>/` and selected through `~/.aer/current`. The exact semantic version, source Git commit, bundle SHA-256 and installation time are recorded in `install.json` and `active.json`.

The Agent Skill is installed only in user-level locations. The installer accepts no target-repository path.

## Self-update

Check the configured update channel:

```bash
python ~/.aer/current/aer_cli.py check-update
```

Update only when the channel exposes a newer semantic version:

```bash
python ~/.aer/current/aer_cli.py update
```

The updater resolves the remote commit first, reads the version from that exact commit, downloads that exact commit, rebuilds and integrity-verifies the bundle, installs the new pinned version, and then switches the `current` pointer. A commit change without a semantic version bump is rejected.

The default channel is the AER repository `main` branch. Controlled environments can use another stable branch or tag as the channel:

```bash
python ~/.aer/current/aer_cli.py check-update --ref release
python ~/.aer/current/aer_cli.py update --ref release
```

## Version pinning

Every installation records:

`semantic version -> exact source Git commit -> bundle SHA-256`

The same semantic version cannot be overwritten by a different commit. This keeps an installed version reproducible even when a mutable branch moves later.

The `current` pointer is the active selection. Previous pinned versions remain available for rollback.

## Rollback

Rollback to the most recently installed different version:

```bash
python ~/.aer/current/aer_cli.py rollback
```

Or select an exact version:

```bash
python ~/.aer/current/aer_cli.py rollback --version 20.1.0
```

Rollback affects only AER's user-scoped installation and already-selected user-level Agent Skill surfaces.

## Repository isolation contract

The installer, updater and rollback commands:

- never create, replace, delete, or back up `.ai-harness` in a project;
- never add AER files to the project's working tree or Git index;
- never modify `.git/config`, hooks, remotes, branches, or ignore files;
- never modify project source, tests, manifests, or configuration merely to install AER;
- never silently modify MCP configuration, credentials, permissions, production access, or merge authority.

A clean target repository therefore stays unchanged when AER is installed, updated, or rolled back.

When AER performs an actual user-requested engineering task, changes to project files are the requested engineering changes—not AER distribution artifacts.

## Lifecycle

```text
pinned installation
      |
  check-update
      |
resolve exact commit + semantic version
      |
download exact source
      |
build + SHA-256 verify
      |
install new version pin
      |
switch user-level current pointer
      |
observe -> learn -> regression -> shadow -> canary -> promote -> monitor
      |
    rollback
```

Learned behavior remains advisory and safety/security controls remain authoritative.
