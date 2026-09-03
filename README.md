# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, optional code intelligence, verification, review, repair, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## Portable, isolated AER distribution

AER is distributed as a versioned offline ZIP bundle. The installed control plane lives under the user's machine-scoped `~/.aer` directory and the Agent Skill remains in user-level skill locations. A target repository is only a workspace; AER installation/update never vendors AER files into it.

### 1. Get the AER bundle

There are two supported ways to get the bundle.

**Download a CI-built bundle**

1. Open the repository's **Actions** tab.
2. Open the latest successful **AER Portable Bundle** workflow run.
3. Download the `aer-portable` artifact and save it as `aer-portable.zip`.

The CI bundle has already passed the portable test suite, bundle build, and bundle integrity verification.

**Build the bundle locally**

From a checkout of the repository:

```bash
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure
python aer.py build --output aer-portable.zip
```

The build records the semantic version, exact source Git commit, and bundle contents in the bundle manifest.

### 2. Verify the bundle

Before installing a bundle obtained from another machine or from CI, verify it:

```bash
python aer.py verify aer-portable.zip
```

A successful verification confirms that the manifest exists, the bundle format is supported, the bundle is marked repository-isolated, an exact source commit is pinned, and every packaged file matches its recorded SHA-256 hash.

### 3. Install AER

Run the installer from the bundle's extracted repository checkout:

```bash
python aer.py install aer-portable.zip
```

AER is installed under:

```text
~/.aer/versions/v<version>/
```

and the active version is selected through:

```text
~/.aer/current
```

The installation records the semantic version, exact source Git commit, bundle SHA-256, and installation metadata in `install.json` and `active.json`.

The installer does **not** require a target repository path and does not modify the project where you will use AER.

### 4. Use the installed AER

The active AER launcher is:

```bash
python ~/.aer/current/aer.py --help
```

From there, use the normal AER commands for your engineering workflow. AER reads the target repository as the workspace for a requested task; its own installation remains under `~/.aer`.

### 5. Check for updates

```bash
python ~/.aer/current/aer.py check-update
```

The updater resolves the exact remote commit and compares it with the installed version/commit pin.

### 6. Update AER

```bash
python ~/.aer/current/aer.py update
```

The update flow resolves the exact remote commit, reads the version from that exact commit, downloads that commit, rebuilds and verifies the bundle, installs the new pinned version, and switches the user-level `current` pointer.

### 7. Roll back

Rollback to the previous installed version:

```bash
python ~/.aer/current/aer.py rollback
```

Or select an exact installed version:

```bash
python ~/.aer/current/aer.py rollback --version 20.1.0
```

### 8. Optional release channel

For a controlled release channel:

```bash
python ~/.aer/current/aer.py check-update --channel release
python ~/.aer/current/aer.py update --channel release
```

See `portable/README.md` for the complete distribution, pinning, update and isolation contract.

## Repository isolation

AER installation, update and rollback do **not** create, replace, delete or back up `.ai-harness` in the project. They do not add AER files to the working tree or index and do not modify `.git/config`, hooks, remotes, branches, or ignore files. MCP configuration, credentials, permissions, production access and merge authority are also untouched.

AER may read the target repository and, when the user requests an engineering task, change the project's own source/tests/configuration. Those are task changes, not AER distribution artifacts.
