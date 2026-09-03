# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, optional code intelligence, verification, review, repair, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## Portable, isolated AER distribution

AER is distributed as a versioned offline bundle. The installed control plane lives under the user's machine-scoped `~/.aer` directory and the Agent Skill remains in user-level skill locations. A target repository is only a workspace; AER installation/update never vendors AER files into it.

Build and verify a pinned bundle:

```bash
python aer.py build --output aer-portable.zip
python aer.py verify aer-portable.zip
```

Install it on another machine:

```bash
python aer.py install aer-portable.zip
```

Each installation records the semantic AER version, exact source Git commit, and bundle SHA-256. A semantic version cannot silently move to another commit.

### Self-update

Check the configured channel:

```bash
python ~/.aer/current/aer.py check-update
```

Update only when the channel exposes a newer semantic version:

```bash
python ~/.aer/current/aer.py update
```

AER resolves the exact remote commit, reads the version from that exact commit, downloads that commit, rebuilds and verifies the bundle, installs the new pinned version, then switches the user-level `current` pointer. A changed commit without a newer version is rejected.

For a controlled release channel:

```bash
python ~/.aer/current/aer.py check-update --channel release
python ~/.aer/current/aer.py update --channel release
```

Rollback to a previous installed version:

```bash
python ~/.aer/current/aer.py rollback
python ~/.aer/current/aer.py rollback --version 20.1.0
```

See `portable/README.md` for the complete distribution, pinning, update and isolation contract.

## Repository isolation

AER installation, update and rollback do **not** create, replace, delete or back up `.ai-harness` in the project. They do not add AER files to the working tree or index and do not modify `.git/config`, hooks, remotes, branches, or ignore files. MCP configuration, credentials, permissions, production access and merge authority are also untouched.

AER may read the target repository and, when the user requests an engineering task, change the project's own source/tests/configuration. Those are task changes, not AER distribution artifacts.
