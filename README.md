# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, capability routing, verification, review, repair, durable evidence, and evidence-backed learning.

## AER CLI naming

The public command-line entry point is **`aer_cli.py`**.

The portable distribution implementation is **`portable/aer_runtime.py`**.

The old `aer.py` launcher name has been retired. Do not use or reference it.

## Quick start

```bash
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure

# Build
aer_build="aer-portable.zip"
python aer_cli.py build --output "$aer_build"

# Verify
python aer_cli.py verify "$aer_build"

# Install - auto-detects Claude Code and activates the plugin
python aer_cli.py install "$aer_build"
```

After installation, restart Claude Code or run `/reload-plugins`. Then confirm:

```text
/plugin
```

The Installed tab should contain `adaptive-ai-coding-orchestrator`. The skill is exposed as:

```text
/adaptive-ai-coding-orchestrator:ai-coding-orchestrator
```

For engineering prompts, the plugin's `UserPromptSubmit` hook also injects a small AER control-plane reminder before Claude processes the prompt. This is what makes AER behavior active instead of leaving the skill as a passive file on disk.

After installation:

```bash
python ~/.aer/current/aer_cli.py check-update
python ~/.aer/current/aer_cli.py update
python ~/.aer/current/aer_cli.py rollback
```

## Artifacts

| Artifact | Description |
|---|---|
| [`aer_cli.py`](aer_cli.py) | Public AER command-line entry point |
| [`portable/aer_runtime.py`](portable/aer_runtime.py) | Portable AER runtime used by the CLI and distribution bundle |
| `aer-portable.zip` | Versioned portable AER distribution produced by CI |

The latest successful CI run publishes the `aer-portable` ZIP as a workflow artifact.

## What AER is

AER is the **control plane around an AI coding agent**, not another coding model. It helps an agent decide what evidence to collect, which capabilities are justified, how much context to consume, when to verify, when to review or repair, and what should be remembered for future work.

The normal lifecycle is:

```text
Understand
  -> Profile repository
  -> Protect task contract
  -> Retrieve evidence
  -> Route capabilities
  -> Execute
  -> Verify
  -> Review
  -> Repair when justified
  -> Learn from evidence
  -> Stop
```

AER normally performs one bounded adaptive run. It does not recursively loop forever unless the user explicitly requests a bounded loop.

## Key capabilities

| Capability | Purpose |
|---|---|
| Repository profiling | Understand instructions, structure, dependencies, git state, tests, and local patterns |
| Protected intent | Preserve goal, scope, constraints, and acceptance criteria through execution and retries |
| Evidence-driven execution | Prefer repository evidence and deterministic verification over model confidence |
| Adaptive routing | Select only the planner, explorer, researcher, builder, verifier, reviewer, security, or RCA capability needed |
| Context optimization | Rank, bound, cache, and compact evidence to reduce context waste |
| Learning engine | Learn from verified outcomes and reviewer findings without changing safety authority |
| Policy registry | Keep learned behavior governed by explicit policies and immutable safety controls |
| Regression replay | Test candidate strategies against deterministic regression cases before promotion |
| Shadow/canary | Evaluate new behavior without immediate activation and promote only when gates pass |
| Rollback | Restore the previous known-good AER version or learned strategy |
| Repository isolation | Keep AER installation under `~/.aer` rather than modifying target repositories |
| Provider neutrality | Keep the engineering contract independent of a specific coding model/provider |

## Portable distribution

AER is distributed as a versioned offline ZIP bundle. The installed control plane is machine-scoped under `~/.aer`; the target repository remains a workspace.

### Prerequisites

- Python 3.11 or later for the portable tooling
- Git when building from source
- Claude Code or another compatible coding agent for AI-assisted engineering

### Build locally

```bash
python aer_cli.py build --output aer-portable.zip
```

The bundle records the exact source Git commit, semantic version, and file SHA-256 values. The Claude plugin metadata is included in the bundle so installation is self-contained.

### Verify

```bash
python aer_cli.py verify aer-portable.zip
```

### Install

Recommended:

```bash
python aer_cli.py install aer-portable.zip
```

The launcher now defaults to provider auto-detection. If Claude Code is on `PATH`, AER registers the local `adaptive-ai-engineering` marketplace and installs `adaptive-ai-coding-orchestrator` at user scope. You can still explicitly choose:

```bash
python aer_cli.py install aer-portable.zip --skill claude
python aer_cli.py install aer-portable.zip --skill agents
python aer_cli.py install aer-portable.zip --skill gemini
python aer_cli.py install aer-portable.zip --skill all
```

Supported skill targets are `agents`, `claude`, `gemini`, `all`, `auto`, and `none`.

### CI bundle

A successful CI run builds and verifies the portable bundle before publishing the artifact. The CI verification also checks that the Claude plugin manifest, skill, and UserPromptSubmit hook are present in the bundle.

## Installed version and provenance

AER stores the active installation under:

```text
~/.aer/versions/v<version>/
~/.aer/current
~/.aer/current/install.json
~/.aer/active.json
```

The provenance chain is:

```text
semantic version -> exact source Git commit -> bundle SHA-256
```

The same semantic version cannot silently be overwritten by a different source commit.

## Update and rollback

```bash
python ~/.aer/current/aer_cli.py check-update
python ~/.aer/current/aer_cli.py update
python ~/.aer/current/aer_cli.py rollback
```

You can select an explicit update channel/reference:

```bash
python ~/.aer/current/aer_cli.py check-update --ref main
python ~/.aer/current/aer_cli.py update --ref main
```

Previous pinned versions remain available for deterministic rollback.

## Repository isolation and safety

Installing, updating, or rolling back AER does not:

- add AER files to the target repository;
- modify project source, tests, manifests, or configuration merely to install AER;
- modify `.git/config`, hooks, remotes, branches, or ignore files;
- silently modify MCP configuration, credentials, permissions, production access, or merge authority;
- allow learned behavior to weaken immutable safety or security controls.

When AER performs a user-requested engineering task, project changes are the requested engineering changes, not AER distribution artifacts.

## Engineering State Ledger

For non-trivial work, AER maintains a traceable state flow:

```text
INTENT
  -> CONTRACT
  -> REPO_FACTS
  -> DECISIONS
  -> EVIDENCE
  -> CHANGESET
  -> VERIFY
  -> OUTCOME
  -> OPEN_RISKS
  -> NEXT
```

This keeps decisions, evidence, changes, verification, and open risks connected.

## Capability roles

| Role | Typical use |
|---|---|
| Planner | Break down substantial implementation work |
| Explorer | Trace repository structure and dependencies |
| Researcher | Gather external/domain evidence when permitted |
| Builder | Implement requested code/configuration/test changes |
| Verifier | Run and interpret deterministic verification |
| Reviewer | Check correctness, compatibility, quality, and maintainability |
| Security reviewer | Examine elevated-risk changes and boundaries |
| RCA investigator | Diagnose without patching when investigation-only work is requested |

Independent read-only work can be parallelized. Edits to the same file are not parallelized.

## Learning and self-improvement

AER's self-improvement loop is evidence-based:

```text
observe
  -> record outcome
  -> learn candidate strategy
  -> update policy proposal
  -> replay regression corpus
  -> shadow evaluation
  -> canary evaluation
  -> promote when gates pass
  -> monitor
  -> rollback when required
```

Learned recommendations remain advisory until the required evidence and regression gates pass. Safety and security policy remain authoritative.

## Typical requests

**Bug fixing**

```text
Fix the failing login test. Inspect repository instructions and the existing authentication flow first. Identify the root cause with evidence, make the smallest compatible change, run the relevant tests, and report what changed and what was verified.
```

**Feature development**

```text
Add retry handling to the outbound payment client. Preserve current API behavior, inspect existing retry and timeout patterns, implement the smallest safe change, add regression coverage, verify it, and report open risks.
```

**RCA**

```text
Investigate why the nightly import occasionally drops records. Do not modify code. Trace the data flow and return facts, inferences, unknowns, root-cause confidence, and evidence.
```

**Code review**

```text
Review this change for correctness, compatibility, security, regression risk, observability, and missing verification. Do not rewrite unrelated code.
```

## Operational recommendations

1. Keep repository instructions and acceptance criteria explicit.
2. Give AER the smallest useful scope.
3. Require deterministic verification for meaningful changes.
4. Use RCA mode when diagnosis must not modify code.
5. Build distributable bundles from known commits and verify them before installation.
6. Keep project-specific AER artifacts out of source control unless intentionally required.
7. Treat learned recommendations as advisory until they have enough evidence and regression coverage.
8. For Claude Code, verify the plugin is present in `/plugin > Installed` after installation.

## Reference documentation

See [`portable/README.md`](portable/README.md) for the detailed distribution, version-pinning, update, rollback, lifecycle, and repository-isolation contract.

## Architecture at a glance

```text
User task / Jira / bug / review / research
                  |
                  v
        +-----------------------+
        |     AER control plane |
        |-----------------------|
        | Intent + Contract     |
        | Repo profiling        |
        | Evidence retrieval    |
        | Context budget/cache  |
        | Capability routing    |
        | Execution controls    |
        | Verification + review |
        | Learning + policies   |
        | Regression replay     |
        | Shadow / Canary       |
        +-----------+-----------+
                    |
                    v
         Compatible coding agent
                    |
                    v
              Target repository

Machine-scoped AER state:
~/.aer/
```

The guiding principle is simple: **use AI for engineering speed, use AER for engineering discipline.**
