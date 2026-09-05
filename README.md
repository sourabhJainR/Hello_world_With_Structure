# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, capability routing, verification, review, repair, durable evidence, graph orchestration, regression replay, and evidence-backed learning.

## AER CLI naming

The **downloadable portable bundle is self-contained**. It includes the application launcher **`app_cli.py`**, the portable runtime, AER skills, and Claude Code plugin metadata.

The source repository also contains the developer/build launcher `aer_cli.py`. You normally do **not** need the source checkout to install AER on a target machine.

## Quick start — install from the portable ZIP

1. Download the `aer-portable.zip` artifact from a successful GitHub Actions run.
2. Extract the ZIP to a local directory.
3. Open a terminal in the extracted AER directory.
4. Run the bundled application CLI.

### Windows PowerShell

```powershell
Expand-Archive .\aer-portable.zip -DestinationPath .\aer
cd .\aer
python .\app_cli.py install
```

### macOS / Linux

```bash
unzip aer-portable.zip -d aer
cd aer
python3 ./app_cli.py install
```

The bundle is intended to be portable: `app_cli.py` discovers the bundled runtime and installs AER into the user-level `~/.aer` location. The target repository is not used as an installation location.

If Claude Code is installed and available on `PATH`, the installer also registers the bundled local Claude marketplace and installs the `adaptive-ai-coding-orchestrator` plugin at user scope.

You can explicitly select the Claude integration:

```bash
python app_cli.py install --skill claude
```

For a machine without Claude Code, install the AER runtime first and add Claude later; the AER installation remains provider-neutral.

## Verify the installation

From the extracted bundle directory:

```bash
python app_cli.py verify
```

Then check the installed AER state:

```bash
python ~/.aer/current/aer_cli.py check-update
```

For Claude Code, restart Claude Code or run:

```text
/reload-plugins
```

Then open:

```text
/plugin
```

The Installed tab should contain:

```text
adaptive-ai-coding-orchestrator
```

The AER skill is exposed as:

```text
/adaptive-ai-coding-orchestrator:ai-coding-orchestrator
```

For normal engineering prompts, the plugin's `UserPromptSubmit` hook injects a small AER control-plane reminder before Claude processes the prompt. The detailed skill is then available for repository-aware engineering work.

## Upgrade existing installations

If AER was installed from an earlier portable artifact, **do not reinstall files manually and do not copy the new orchestration files into repositories**. Update the existing machine-scoped installation:

```bash
python ~/.aer/current/aer_cli.py check-update --ref main
python ~/.aer/current/aer_cli.py update --ref main
python ~/.aer/current/aer_cli.py check-update
```

The update installs the new pinned AER bundle, including the graph orchestration runtime and updated `ai-coding-orchestrator` skill, then switches the user-level `~/.aer/current` pointer. Existing repositories remain untouched.

After updating Claude Code, reload the plugin:

```text
/reload-plugins
```

Then verify:

```text
/plugin
```

The updated skill now applies the graph-aware lifecycle:

```text
Intent / Contract
      -> Repository evidence
      -> Capability plan
      -> Dependency-aware graph
      -> Agent execution
      -> Bounded Plan / Act / Observe / Evaluate loop
      -> Graph gates / joins
      -> Verification / Review
      -> Targeted Repair + Re-evaluation
      -> Regression Replay
      -> Learning Candidate
      -> Shadow / Canary
      -> Promote / Monitor / Rollback
```

This is a behavior and runtime update to AER; it does not require AER files to be added to the project repository.

## Using AER after installation

Once installed, AER is machine-scoped. You can work in any repository without copying AER files into that repository.

Start Claude Code from the repository you want to work on:

```bash
claude
```

Then give Claude a normal engineering request, for example:

```text
Fix the failing login test. Inspect repository instructions and the existing authentication flow first. Identify the root cause with evidence, make the smallest compatible change, run the relevant tests, and report what changed and what was verified.
```

Or invoke the AER skill explicitly:

```text
/adaptive-ai-coding-orchestrator:ai-coding-orchestrator
```

The intended flow is:

```text
User prompt
    -> AER prompt hook
    -> Contract + repository evidence
    -> Capability plan
    -> Dependency-aware graph
    -> Agent execution with bounded loops
    -> Evaluation gates
    -> Verification + review
    -> Regression replay
    -> Learning / evidence
```

AER is a control plane around Claude Code, not a second coding model. Claude remains responsible for the interactive agent work; AER provides the engineering discipline, evidence flow, graph orchestration, verification, policy, and learning controls.

## Update and rollback

After installation, use the installed CLI rather than the copy in the downloaded ZIP:

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

## Build a new portable bundle from source

If you are developing AER itself, use the source checkout and the developer launcher:

```bash
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure
python aer_cli.py build --output aer-portable.zip
python aer_cli.py verify aer-portable.zip
```

A successful CI run also publishes the portable ZIP as the `aer-portable` workflow artifact. CI verifies that the bundle contains the Claude plugin manifest, marketplace metadata, AER skill, and `UserPromptSubmit` hook.

## What is inside the portable ZIP

The portable ZIP is the distribution unit. The important files are:

```text
aer-portable.zip
|
+-- app_cli.py                         # user-facing bundle launcher
+-- payload/
    +-- portable/aer_runtime.py       # AER runtime
    +-- .claude-plugin/
    |   +-- plugin.json               # Claude plugin manifest
    |   +-- marketplace.json          # local marketplace metadata
    +-- skills/
        +-- ai-coding-orchestrator/
            +-- SKILL.md              # graph-aware engineering instructions
            +-- hooks/aer_prompt.py   # UserPromptSubmit hook
```

The extracted bundle is the thing you install and run. Do not manually copy `payload` files into your project.

## Installed state

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
        | Graph orchestration   |
        | Bounded agent loops   |
        | Evaluation gates     |
        | Verification + review |
        | Learning + policies   |
        | Regression replay     |
        | Shadow / Canary       |
        +-----------+-----------+
                    |
                    v
             Claude Code / agent
                    |
                    v
              Target repository

Machine-scoped AER state:
~/.aer/
```

The guiding principle is simple: **use AI for engineering speed, use AER for engineering discipline.**
