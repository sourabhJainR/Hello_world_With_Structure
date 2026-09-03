# AER Portable Distribution

AER is a **machine-scoped, repository-isolated, version-pinned engineering control plane**. Installing or updating AER never vendors its implementation into the repository being worked on.

## Distribution unit

The bundle contains the current provider-neutral AER runtime and canonical Agent Skill, including routing, bounded context, context cache, learning, policy registry, rollback controls, regression corpus, shadow/canary evaluation, verification, capability planning, and optional-extension contracts.

Mutable state is excluded: execution journals, telemetry, learned task logs, worktrees, caches, and other machine/session state.

## Install

```bash
python aer.py install aer-portable.zip
```

AER is installed under `~/.aer/versions/v<version>/` and selected through `~/.aer/current`. The exact semantic version, source Git commit, bundle SHA-256 and installation time are stored in `install.json` and `active.json`.

The Agent Skill is installed only in user-level locations. No target repository path is accepted by the installer.

## Self-update

Check the configured update channel:

```bash
python ~/.aer/current/aer.py check-update
```

Update to the newest channel commit only when it carries a newer semantic version:

```bash
python ~/.aer/current/aer.py update
```

The updater resolves the remote commit first, downloads that **exact commit**, rebuilds and verifies the bundle, installs it into a new immutable version directory, and only then switches the `current` pointer. A changed commit without a version bump is rejected unless explicitly forced.

The default channel is the AER repository `main` branch. For controlled environments, use a stable branch/ref as the channel:

```bash
python ~/.aer/current/aer.py check-update --channel release
python ~/.aer/current/aer.py update --channel release
```

## Version pinning

Each installed version has two pins:

`semantic version -> exact source commit`

A version directory cannot be silently overwritten by another commit. This prevents a mutable branch from changing the meaning of an already-installed version.

The `current` pointer is the only active selection. Older versions remain available for rollback.

## Rollback

Automatic rollback to the previous installed version:

```bash
python ~/.aer/current/aer.py rollback
```

Or select a specific installed version:

```bash
python ~/.aer/current/aer.py rollback --version 20.1.0
```

Rollback changes only AER's user-scoped installation and selected user-level skill surfaces.

## Repository isolation contract

The installer and updater:

- never create, replace, delete, or back up `.ai-harness` in a project;
- never add files to the project's working tree or Git index;
- never modify `.git/config`, hooks, remotes, branches, or ignore files;
- never modify project source, tests, manifests, or configuration merely to install AER;
- never silently change MCP configuration, credentials, permissions, production access, or merge authority.

A target repository can therefore remain completely unchanged by installing, updating, or rolling back AER.

When AER actually performs a user's requested engineering task, changes to the project are the requested engineering changes—not AER distribution artifacts.

## Lifecycle

```text
installed pinned version
        |
     check-update
        |
 download exact commit
        |
 build + integrity verify
        |
 install new immutable version
        |
 atomic current-pointer switch
        |
 observe -> learn -> regressions -> shadow -> canary -> promote -> monitor
        |
      rollback
```

Learned behavior remains advisory and safety/security controls remain authoritative.
