# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** is the engineering control-plane concept behind the orchestrator: it turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, capability routing, verification, review, repair, durable evidence, and evidence-backed learning.

The product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## What AER is

AER is the **control plane around an AI coding agent**, not another coding model. It helps an agent decide what evidence to collect, which capabilities are justified, how much context to consume, when to verify, when to review or repair, and what should be remembered for future work.

The normal lifecycle is:

```text
Understand
   -> Profile repository
   -> Specify protected task contract
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

## Why use AER?

AER is designed to make AI-assisted engineering **more reliable, less wasteful, easier to audit, and safer to operate on real repositories**.

### Key benefits

| Benefit | What AER does | Why it matters |
|---|---|---|
| Repository-aware work | Reads repository instructions, structure, dependencies, git state, tests, and local patterns before editing | Reduces incorrect assumptions and architectural drift |
| Protected intent | Carries a task contract and `intent_digest` through execution, retries, resumes, and handoffs | Prevents silent goal or scope drift |
| Evidence over confidence | Treats verification results as stronger evidence than model confidence | Avoids declaring work complete merely because an agent sounds confident |
| Minimal safe changes | Favors the smallest compatible change and reuses existing patterns | Lowers regression and maintenance risk |
| Adaptive routing | Selects only justified planner, explorer, researcher, builder, verifier, reviewer, security, or RCA capabilities | Avoids unnecessary agent/tool work |
| Context efficiency | Ranks and bounds repository evidence, compacts history, and avoids replaying irrelevant transcripts | Reduces token cost and context rot |
| Durable engineering memory | Records useful outcomes, decisions, regressions, and lessons outside the repository | Future runs can benefit from previous evidence without polluting project source |
| Regression-aware learning | Replays regression cases and evaluates candidate strategies before promotion | Learning is evidence-backed rather than guess-driven |
| Shadow/canary controls | Supports non-mutating shadow evaluation and gated canary promotion | New behavior can be tested before becoming active |
| Safety boundaries | Learned advice cannot grant permissions, credentials, production access, or merge authority | Keeps safety controls authoritative |
| Provider neutrality | Uses a provider-neutral skill/control-plane contract | The same engineering method can work across compatible coding agents |
| Repository isolation | Installs AER under `~/.aer` and keeps the project as a workspace | No AER vendor files are required in every project |

## Portable, isolated AER distribution

AER is distributed as a versioned offline ZIP bundle. The installed control plane lives under the user's machine-scoped `~/.aer` directory and the Agent Skill is installed only into user-level skill locations. A target repository is only a workspace; AER installation and updates do not vendor AER files into it.

### Prerequisites

- Python 3.11 or later is recommended for the portable tooling.
- A Git checkout is needed when building the bundle locally.
- A compatible coding agent is needed to actually perform AI-assisted engineering work using the installed Agent Skill.

### CLI naming

The AER command-line entry point is **`aer_cli.py`**. The portable distribution implementation is **`portable/aer_runtime.py`**. These names are intentionally different so the user-facing CLI is not confused with the internal portable runtime.

If you are working from a source checkout, run the commands below from the repository root. You do not need to locate or download a separate `aer.py` file.

### 1. Get the AER bundle

There are two supported ways to get the bundle.

**Download a CI-built bundle**

1. Open the repository's **Actions** tab.
2. Open the latest successful **AER Portable Bundle** workflow run.
3. Download the `aer-portable` artifact and save it as `aer-portable.zip`.

The CI bundle is produced only after the portable test suite, bundle build, and bundle integrity verification succeed.

**Build the bundle locally**

From a checkout of the repository:

```bash
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure
python aer_cli.py build --output aer-portable.zip
```

For a source checkout, AER records the exact source Git commit in the bundle manifest. Builds intended for distribution should therefore be made from a clean, known commit.

### 2. Verify the bundle

Before installing a bundle obtained from another machine or from CI, verify it:

```bash
python aer_cli.py verify aer-portable.zip
```

Successful verification confirms that the manifest exists, the bundle format is supported, the bundle is marked repository-isolated, an exact source commit is pinned, and packaged files match their recorded SHA-256 hashes.

### 3. Install AER

Run the installer from the repository checkout that contains **`aer_cli.py`**:

```bash
python aer_cli.py install aer-portable.zip
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

By default the canonical Agent Skill is installed to the user-level `~/.agents/skills/ai-coding-orchestrator` location. You can select another supported user-level skill surface explicitly:

```bash
python aer_cli.py install aer-portable.zip --skill agents
python aer_cli.py install aer-portable.zip --skill claude
python aer_cli.py install aer-portable.zip --skill gemini
python aer_cli.py install aer-portable.zip --skill all
```

The installer accepts no target-repository path and does not modify the project where you will use AER.

### 4. Start using AER with a coding agent

After installation, open the **target repository** in your compatible coding agent. The `ai-coding-orchestrator` Agent Skill is user-scoped, so the repository does not need an AER copy checked into source control.

Give the agent a normal engineering request, for example:

```text
Fix the failing login test. First inspect repository instructions and the existing authentication flow.
Identify the root cause with evidence, make the smallest compatible change, run the relevant tests,
and report exactly what changed and what was verified.
```

For a feature request:

```text
Add retry handling to the outbound payment client. Preserve current API behavior,
inspect existing retry/timeout patterns first, implement the smallest safe change,
add or update regression coverage, run verification, and report open risks.
```

For RCA without a requested fix:

```text
Investigate why the nightly import occasionally drops records. Do not modify code.
Trace the data flow, inspect source, tests, logs, persistence and integration boundaries,
and return facts, inferences, unknowns, root-cause confidence, and evidence.
```

For a code review:

```text
Review this change for correctness, compatibility, security, regression risk,
observability, and missing verification. Do not rewrite unrelated code.
```

AER guides the agent through repository understanding, protected intent, evidence retrieval, capability selection, implementation or analysis, verification, review, and learning. The exact agent UI/command depends on the provider; AER itself does not require a provider-specific invocation command.

### 5. What happens during a typical AER run

For non-trivial work, AER maintains an Engineering State Ledger:

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

A typical implementation run therefore looks like:

1. **Understand** the request and identify ambiguity that could materially affect correctness, safety, architecture, scope, or verification.
2. **Profile** the repository, instructions, dependencies, git state, relevant symbols, tests, and existing conventions.
3. **Specify** the goal, non-goals, requirements, constraints, protected behavior, boundaries, acceptance criteria, risks, and assumptions.
4. **Retrieve** only the evidence needed for the task, using bounded context and targeted searches.
5. **Route** only the capabilities that are justified by the task and risk.
6. **Execute** the requested change using existing repository patterns and the smallest safe surface.
7. **Verify** with repository-native commands and relevant regression checks.
8. **Review** the final diff and architecture/security/operational implications where relevant.
9. **Repair** only when new evidence justifies another change.
10. **Learn** from verified outcomes, reviewer findings, retries, and regressions without silently changing safety authority.
11. **Stop** when the acceptance criteria are met or when budget, evidence, regression risk, or diminishing returns says to stop.

### 6. Understand the roles AER can use

AER can select capability roles according to task need instead of invoking everything for every request.

| Role | Typical use |
|---|---|
| Planner | Break down substantial implementation work |
| Explorer | Trace repository structure, call paths, and dependencies |
| Researcher | Gather external or domain evidence when permitted |
| Builder | Implement the requested code/configuration/test change |
| Verifier | Run and interpret deterministic verification |
| Reviewer | Check correctness, compatibility, quality, and maintainability |
| Security reviewer | Examine elevated-risk changes and boundaries |
| RCA investigator | Diagnose without patching when the request is investigation-only |

Independent read-only work can be parallelized. Edits to the same file are not parallelized.

### 7. Use AER for different kinds of engineering work

**Bug fixing**

Ask AER to reproduce or trace the issue, prove the root cause, make the smallest compatible fix, and verify the affected paths.

**Feature development**

Give the desired behavior and acceptance criteria. AER can profile the repository, identify existing extension points, plan the work, implement it, add regression coverage, and verify the final result.

**RCA / production investigation**

Explicitly say **do not modify code** when you only want diagnosis. AER's RCA contract keeps the investigation analysis-only and separates facts, inferences, unknowns, and recommendations.

**Code review**

Ask for evidence-backed review focused on correctness, compatibility, security, regression risk, observability, and verification rather than cosmetic rewrites.

**Refactoring**

Ask AER to preserve behavior, identify callers and integration boundaries, and use characterization/regression tests before broad structural changes.

**POCs and research**

Ask AER to compare approaches, keep assumptions explicit, and separate exploratory findings from production-ready recommendations.

### 8. Check the installed AER version

The user-scoped installation keeps the active version and provenance in:

```text
~/.aer/current/install.json
~/.aer/active.json
```

You can inspect them directly:

```bash
cat ~/.aer/current/install.json
cat ~/.aer/active.json
```

The important provenance chain is:

```text
semantic version -> exact source Git commit -> bundle SHA-256
```

### 9. Check for updates

```bash
python ~/.aer/current/aer_cli.py check-update
```

The updater resolves the exact remote commit and compares both the installed semantic version and exact source commit. A changed commit at the same semantic version is treated as an update candidate rather than being silently ignored.

### 10. Update AER

```bash
python ~/.aer/current/aer_cli.py update
```

The update flow resolves the exact remote commit, reads the version from that exact commit, downloads that commit, rebuilds and verifies the bundle, installs the new pinned version, and switches the user-level `current` pointer.

You can explicitly choose the source ref used as the update channel:

```bash
python ~/.aer/current/aer_cli.py check-update --ref main
python ~/.aer/current/aer_cli.py update --ref main
```

A changed commit is never allowed to overwrite an existing installation that is already pinned to another commit under the same semantic version.

### 11. Roll back

Rollback to the most recently installed different immutable version:

```bash
python ~/.aer/current/aer_cli.py rollback
```

Rollback changes only the user-scoped AER installation and selected user-level Agent Skill surfaces. Project files are not modified by the rollback operation.

### 12. Choose skill installation surfaces

Supported install targets are:

```text
agents  -> ~/.agents/skills/ai-coding-orchestrator
claude  -> ~/.claude/skills/ai-coding-orchestrator
gemini  -> ~/.gemini/skills/ai-coding-orchestrator
all     -> all supported locations
auto    -> currently existing supported locations
none    -> do not install a skill copy
```

For example:

```bash
python aer_cli.py install aer-portable.zip --skill all
```

Use the skill surface that matches the coding-agent environment you actually use.

## Repository isolation and safety

AER installation, update and rollback do **not**:

- create, replace, delete, or back up `.ai-harness` in the project;
- add AER files to the working tree or Git index;
- modify `.git/config`, hooks, remotes, branches, or ignore files;
- modify project source, tests, manifests, or configuration merely to install AER;
- silently modify MCP configuration, credentials, permissions, production access, or merge authority.

A clean target repository therefore stays unchanged when AER is installed, updated, or rolled back.

When AER performs an actual user-requested engineering task, changes to project files are the requested engineering changes—not AER distribution artifacts.

Learned behavior is advisory. Immutable safety and security controls remain authoritative and cannot be weakened by learned policies.

## What AER does not replace

AER does not replace:

- your source repository and its ownership model;
- your CI/CD system;
- code review and human engineering judgment;
- your coding-agent provider/model;
- repository-specific security and compliance controls.

AER is a control and evidence layer around those systems.

## Operational recommendations

For the most reliable results:

1. Keep repository instructions and acceptance criteria explicit.
2. Give AER the smallest useful scope when diagnosing or changing a system.
3. Require verification for changes that matter; do not treat model confidence as proof.
4. Use the RCA mode when you want diagnosis without modifications.
5. Build distributable bundles from known commits and verify them before installation.
6. Keep project-specific AER artifacts out of source control unless you intentionally want repository-local artifacts.
7. Treat learned recommendations as advisory until they have enough evidence and regression coverage.

## Portable bundle reference

For the detailed distribution, pinning, update, rollback, isolation, and lifecycle contract, see [`portable/README.md`](portable/README.md).

## Quick reference

```bash
# Get source
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure

# Build
aer_build="aer-portable.zip"
python aer_cli.py build --output "$aer_build"

# Verify
python aer_cli.py verify "$aer_build"

# Install
python aer_cli.py install "$aer_build" --skill agents

# Inspect installed provenance
cat ~/.aer/current/install.json

# Check and update
python ~/.aer/current/aer_cli.py check-update
python ~/.aer/current/aer_cli.py update

# Roll back
python ~/.aer/current/aer_cli.py rollback
```

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
