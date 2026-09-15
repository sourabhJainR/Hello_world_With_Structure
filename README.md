# Adaptive AI Coding Orchestrator

A provider-neutral AI software-engineering control plane for Claude Code and compatible coding agents. **AER (Adaptive Engineering Runtime)** turns a natural-language task, Jira issue, bug, review, research question, or POC into a repository-aware workflow with bounded context, capability routing, verification, review, durable evidence, graph orchestration, regression replay, and evidence-backed learning.

## Current repository state

The repository now has a coherent execution path from task intake through verification and learning. The latest architecture combines the existing AER lifecycle with a provider-neutral state-graph runtime and dependency-aware agent teams without introducing a LangGraph runtime dependency.

The important ownership boundaries are:

- **`portable.task_planner.TaskPlan`** owns dependency planning for agent work.
- **`portable.agency_state_graph.StateGraph`** owns low-level graph execution semantics: state, reducers, routing, bounded retries, checkpoints, interrupts, traces, and bounded supersteps.
- **`.ai-harness/runtime/graph_agent_team.py`** owns high-level role orchestration and task-scoped `SharedTaskMemory` while using `TaskPlan` as its canonical dependency contract.
- **`portable.agent_capabilities` / `CapabilityFabric`** owns capability semantics, risk, fallback, sandbox/network requirements, and provider selection.
- **`portable.agent_capabilities.PersistentMemory`** owns durable memory semantics; compatibility memory APIs adapt to it rather than creating a second store.
- **`portable.agency_codebase_context.CodebaseIndex`** owns semantic repository retrieval, while `RepositoryIntelligence` provides broader bounded repository packing.
- **`portable.repo_intelligence.RepositoryMap`** owns the deterministic repository snapshot and structural question surface: ranked search, callers/callees, impact, affected-test candidates, situational changes, and bounded task packs.

See [`docs/CAPABILITY_MEMORY_OWNERSHIP.md`](docs/CAPABILITY_MEMORY_OWNERSHIP.md) for the explicit ownership contract and [`docs/RIPWIRE_INTEGRATION.md`](docs/RIPWIRE_INTEGRATION.md) for the repository-intelligence design lineage.

## Deterministic repository intelligence

AER now has a dependency-free repository map designed for the first minutes of an engineering task. It builds one deterministic snapshot and reuses that model for multiple questions instead of making each feature invent its own index.

```bash
python -m portable.repo_intelligence . --for="Fix the authentication timeout regression" --token-budget=4000
python -m portable.repo_intelligence . --mode=callers --symbol="authenticate"
python -m portable.repo_intelligence . --mode=impact --symbol="authenticate" --graph-depth=1
python -m portable.repo_intelligence . --mode=tests --symbol="authenticate"
python -m portable.repo_intelligence . --mode=situ --base=HEAD
python -m portable.repo_intelligence . --mode=pack-task --for="Add retry handling to the payment client"
```

The output is deliberately evidence-oriented:

- deterministic file ordering and SHA-256 snapshot identity;
- lightweight symbol/import/call relationships without external services;
- bounded graph expansion with confidence on ambiguous edges;
- explicit token budgets and whole evidence windows rather than arbitrary truncation;
- affected-test candidates without pretending they prove coverage;
- skipped-file and parser-error disclosure;
- explicit unknowns whenever context was omitted or the graph could not establish a relationship;
- compact output suitable for coding-agent handoff, plus JSON for programmatic use.

The map is an accelerator, not a verification oracle. Verification, policy, permissions, review, regression, and release gates remain authoritative.

## Executable engineering lifecycle

For substantial work the control plane follows one evidence lineage:

```text
research -> plan -> implement -> verify -> review -> shadow -> canary -> promote
                                                            |
                                                            +-> rollback
```

`ContextEvidence` is immutable. Verification creates a `VerificationReceipt`; review creates a `ReviewReceipt` bound to the same artifact, evidence, and verification. Shadow and canary require the review receipt. Promotion requires matching verification/review receipts and the artifact already in canary. Release history records the relevant digests.

The broader runtime also supports bounded Plan / Act / Observe / Evaluate loops, regression replay, learning candidates, and guarded promotion. Learned recommendations remain advisory until replay, confidence, and canary gates pass.

## Graph orchestration

AER includes a dependency-free `StateGraph` runtime inspired by useful durable-agent-graph patterns without importing LangGraph. It provides:

- explicit mutable execution state with immutable node snapshots;
- per-key reducers for deterministic parallel state merges;
- conditional routing and normal graph edges;
- bounded per-node retry policies;
- checkpoint-after-superstep durability through a host-supplied checkpoint store;
- before/after node interrupts for controlled pause and resume;
- deterministic execution traces and run digests;
- bounded execution with `max_steps` protection;
- bounded parallel supersteps for nodes explicitly marked parallel-safe.

The runtime is deliberately small and provider-neutral. It orchestrates callbacks supplied by the host; it does not execute shell commands, credentials, model calls, repository mutations, or tools by itself.

### Agent-team integration

`GraphAgentTeam` uses the state graph as its execution engine while preserving the existing public contract:

```text
TaskPlan
   |
   v
Dependency graph
   |
   +--> independent read-only agents -- bounded parallel supersteps
   |
   +--> mutating agents ------------ serialized execution
   |
   v
SharedTaskMemory
   |
   v
Verification / review / synthesis
```

Dependency failures remain fail-closed. Blocked downstream roles are represented in graph state but are not reported as executed agent results. Read-only roles receive an explicit `patch_allowed: false` execution guard in the harness bridge.

The graph integration is enabled by default. For diagnostics, the legacy phase execution path can be selected with:

```bash
AER_GRAPH_TEAM=0
```

This fallback exists for compatibility and diagnostics; the graph path is the default execution model.

## State graph and agent-team verification

The repository includes dedicated coverage for:

- reducer-based parallel state merging;
- conditional routing;
- bounded retry behavior;
- checkpoint and resume behavior without repeating completed agents;
- before/after interrupts;
- max-step protection;
- canonical `TaskPlan` dependency planning;
- shared-memory propagation between agents;
- bounded parallel read-only execution;
- serialized mutating execution;
- dependency blocking and cycle rejection;
- graph-phase construction and portable-bundle validation.

The graph-specific CI workflow compiles the AER runtime, runs the graph and resilience suites plus `.ai-harness/tests`, and validates a fresh portable bundle. See [`.github/workflows/graph-runtime-check.yml`](.github/workflows/graph-runtime-check.yml).

## AER CLI and portable distribution

The **GitHub Actions `aer-portable` artifact is self-contained**. The downloaded artifact contains both the user-facing launcher **`aer_cli.py`** and the distribution bundle **`aer-portable.zip`** at the artifact root.

Bootstrap from a downloaded artifact:

```bash
python aer_cli.py aer-portable.zip
```

On success, AER is installed under the user-level `~/.aer` location.

Published artifact layout:

```text
aer-portable/
├── aer_cli.py
├── aer-portable.zip
├── portable-tests.log
└── run-metadata.txt
```

The portable ZIP is also self-contained and includes its launcher:

```bash
python aer_cli.py install
```

Windows PowerShell:

```powershell
python .\aer_cli.py .\aer-portable.zip
```

macOS / Linux:

```bash
python3 ./aer_cli.py ./aer-portable.zip
```

If Claude Code is available on `PATH`, the installer can register the bundled local Claude marketplace and install the `adaptive-ai-coding-orchestrator` plugin at user scope.

Explicit Claude integration:

```bash
python aer_cli.py install aer-portable.zip --skill claude
```

AER remains provider-neutral when Claude Code is not installed.

## Verify the installation

From the published artifact directory:

```bash
python aer_cli.py aer-portable.zip
```

Then check the installed runtime:

```bash
python ~/.aer/current/aer_cli.py check-update
```

For Claude Code, reload plugins and verify the installed plugin:

```text
/reload-plugins
/plugin
```

The installed skill is:

```text
/adaptive-ai-coding-orchestrator:ai-coding-orchestrator
```

The plugin's prompt hook provides a small AER control-plane reminder, while the detailed skill drives repository-aware engineering work.

## Upgrade, rollback, and provenance

Use the installed CLI rather than manually copying runtime files into projects:

```bash
python ~/.aer/current/aer_cli.py check-update
python ~/.aer/current/aer_cli.py update
python ~/.aer/current/aer_cli.py rollback
```

An explicit source reference can be selected:

```bash
python ~/.aer/current/aer_cli.py check-update --ref main
python ~/.aer/current/aer_cli.py update --ref main
```

The installation records a provenance chain:

```text
semantic version -> exact source Git commit -> bundle SHA-256
```

The same semantic version cannot silently be replaced by a different source commit.

## Build a portable bundle from source

```bash
git clone https://github.com/sourabhJainR/Hello_world_With_Structure.git
cd Hello_world_With_Structure
python aer_cli.py build --output aer-portable.zip
python aer_cli.py verify aer-portable.zip
```

CI verifies the portable distribution, including the Claude plugin manifest, marketplace metadata, AER skill, prompt hook, runtime payload, and bundle integrity.

## What is inside the portable ZIP

```text
aer-portable.zip
|
+-- aer_cli.py
+-- payload/
    +-- portable/aer_runtime.py
    +-- portable/agency_state_graph.py
    +-- portable/repo_intelligence.py
    +-- .claude-plugin/
    |   +-- plugin.json
    |   +-- marketplace.json
    +-- skills/
        +-- ai-coding-orchestrator/
            +-- SKILL.md
            +-- hooks/aer_prompt.py
```

The extracted GitHub Actions artifact places the outer `aer_cli.py` beside `aer-portable.zip` so the bootstrap command works without opening the nested ZIP first. Do not copy `payload` files into the target project.

## Installed machine state

AER stores active installation state under:

```text
~/.aer/versions/v<version>/
~/.aer/current
~/.aer/current/install.json
~/.aer/active.json
```

Execution journals, telemetry, learned task logs, caches, worktrees, and Python caches remain outside the portable distribution.

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

The lifecycle is backed by run manifests, phase checkpoints, verification evidence, review evidence, regression history, and learning-controller records.

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
| Synthesizer | Combine graph evidence, decisions, unresolved risks, and next action |

Independent read-only work can be parallelized. Mutating agents are serialized behind their declared dependencies.

## Repository intelligence

AER uses a layered repository-context model:

1. deterministic snapshot and structural repository map;
2. symbol and relationship-aware retrieval;
3. text retrieval for free-form questions and non-code material;
4. bounded repository packing when broader context is needed.

The repository map is intentionally dependency-free and records uncertainty instead of hiding it. For small edits, normal text and patch tools remain preferred. Structural retrieval is most useful for symbol discovery, callers/callees, impact, hierarchy, cross-file changes, affected-test candidates, and bounded task context.

See [`docs/RIPWIRE_INTEGRATION.md`](docs/RIPWIRE_INTEGRATION.md) for the adopted design principles and explicit non-adoptions.

## Learning and self-improvement

AER's self-improvement loop is evidence-based:

```text
observe
  -> record outcome
  -> learn candidate strategy
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

## Repository map

```text
Hello_world_With_Structure/
├── .ai-harness/                 # adaptive harness, policies, runtime and phase lifecycle
├── portable/                    # dependency-free distributable AER runtime
├── agency/                      # upstream agency assets and provenance
├── skills/                      # canonical local agent skills
├── .agents/                     # compatibility/agent skill surfaces
├── .claude/ + .claude-plugin/   # Claude skill and plugin packaging
├── docs/                        # architecture, lifecycle, research and deployment contracts
├── examples/                    # runnable example applications and harness scenarios
├── scripts/                     # conformance, eval, packaging and validation tooling
├── state/                       # engineering state schema
└── tests/                       # portable and integration regression coverage
```

The repository intentionally contains compatibility and historical documentation surfaces. They are not independent runtime owners; new behavior must be added to the canonical implementation and older surfaces must adapt to it.

## Reference documentation

- [`docs/CAPABILITY_MEMORY_OWNERSHIP.md`](docs/CAPABILITY_MEMORY_OWNERSHIP.md) — canonical capability, memory, and retrieval ownership.
- [`docs/RIPWIRE_INTEGRATION.md`](docs/RIPWIRE_INTEGRATION.md) — deterministic repository-intelligence design lineage and boundaries.
- [`portable/LANGGRAPH_PATTERN_ALIGNMENT.md`](portable/LANGGRAPH_PATTERN_ALIGNMENT.md) — mapping of state-graph patterns to AER constructs.
- [`portable/README.md`](portable/README.md) — portable distribution and machine-scoped lifecycle.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — deployment and runtime integration.
- [`docs/USAGE_AND_PLATFORM_INTEGRATION.md`](docs/USAGE_AND_PLATFORM_INTEGRATION.md) — platform usage and integration.
- [`docs/ENGINEERING_WORK_REPORTS.md`](docs/ENGINEERING_WORK_REPORTS.md) — engineering work-report and evidence flow.
- [`docs/REGRESSION_CANARY.md`](docs/REGRESSION_CANARY.md) — regression, shadow, and canary controls.
- [` .ai-harness/ENGINEERING_DESIGN_POLICY.md`](.ai-harness/ENGINEERING_DESIGN_POLICY.md) — engineering-design guardrails.

## Design principle

**Use AI for engineering speed; use AER for engineering discipline.**
