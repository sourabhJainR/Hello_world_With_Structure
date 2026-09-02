# Coding-agent harness research and adaptation

Reviewed `decodingai-magazine/building-a-coding-agent-from-scratch-course` at the current `main` revision. The repository is an Apache-2.0 open-source course and explicitly treats the harness around the model as the important engineering surface. This document records architectural concepts adapted into this project; it does not copy source implementation.

## What the reference system does well

The reference system separates a small tool-calling agent from a much larger harness. Its published architecture includes a headless agent loop, permissions, local/remote sandboxing, context memory and compaction, an LSP feedback loop, an agents catalog, parallel subagents, durable runtime/replay, observability and benchmark/regression/online evals. It also emphasizes that compaction should happen before the context limit and that evaluation must test whether changes make the system better or worse. See the reference repository README and architecture materials for the source design. 

## Gap analysis against this repository

| Reference concept | Existing state here | Decision | Adaptation |
|---|---|---|---|
| Headless agent loop | Provider-neutral phase runner already exists | Keep | Do not replace provider/host architecture. |
| Agent catalog | Route capabilities and reviewers existed, but roles were implicit | Adapt | Added deterministic capability catalog with mutability, parallel-safety and report contracts. |
| Parallel read-only subagents | Review agents already run independently | Strengthen | Capability plan now exposes which read-only roles can be parallelized; no shared-file parallel mutation. |
| Context compaction | Existing Flash-context engine ranked memory/history but retained a simple bounded slice | Adapt | Added deterministic evidence-priority compaction that prefers acceptance, constraints, decisions, evidence, verification, regressions and risks. |
| Durable runtime/replay | Checkpoint/resume existed, but no append-only execution journal | Adapt | Added hash-chained execution journal and replay projection. Existing checkpoints remain the resume contract. |
| Permissions | Existing execution policy and confirmation gates | Keep | No framework-specific permission layer was imported. The host agent remains responsible for its own tool permission UI. |
| Sandbox | Worktrees and policy existed; provider commands run in the repository environment | Defer | A real Docker/remote executor would be a larger operational boundary and is not safe to bolt on silently. Keep sandbox as an explicit future executor seam. |
| LSP feedback | Not a core dependency | Defer/optional | LSP should be a capability provider discovered when available, not a new mandatory dependency. |
| Memory | Evidence-backed learning, regression events and collaboration graph already exist | Keep + connect | Durable journal and capability plan become additional provenance inputs. |
| Observability | Local JSONL telemetry exists | Strengthen | Every telemetry event is also journaled for replay; journal failure is non-fatal. |
| Evals | Deterministic routing/context/policy suites exist | Strengthen | New deterministic evals cover capability selection, context compaction and journal integrity. Provider-backed evals remain optional. |
| Durable HITL | Existing confirmation gates/checkpoints exist | Keep | Do not add Kitaru or another runtime until an actual remote/durable execution requirement justifies it. |
| Remote swarm | Not required for local coding skill | Defer | Parallelism is useful only where independent work has measurable value. |

## Implemented changes

### 1. Capability catalog

`runtime/capability_catalog.py` provides a small language-neutral catalog:

- planner
- explorer
- researcher
- builder
- verifier
- reviewer
- security reviewer
- RCA investigator

Each role declares whether it can mutate, whether it is safe to parallelize, the minimum risk tier and its report contract. Selection is deterministic and produces `capability-plan.json` for every orchestrated run.

This closes a subtle gap: the system previously knew about reviewers and capabilities but did not expose a first-class, inspectable specialist plan before execution.

### 2. Evidence-priority context compaction

`context_engine.py` now removes repeated low-value history before the model boundary and prioritizes proof-bearing material. It is deterministic and does not invent summaries.

The policy remains:

`retrieve -> rank -> compact -> preserve proof -> send minimum sufficient context`

This is inspired by the reference project's context-compaction approach, not a copy of its implementation.

### 3. Durable execution journal

`runtime/run_journal.py` adds:

- append-only execution events;
- monotonically increasing sequence numbers;
- previous-hash links;
- per-record SHA-256 digest;
- chain verification;
- compact phase/run replay projection.

`observability.emit_event()` mirrors normal events into this journal. Journal failure never fails the actual run.

The distinction is intentional:

- checkpoint = resumable state;
- telemetry = operational observation;
- journal = durable ordered execution history;
- manifest = run result and verification state.

### 4. Deterministic specialist planning

`run.py` creates and validates the capability plan before provider execution and includes the compact plan in the provider prompt. The provider is told to use only the selected roles and honor each report contract.

## Deliberately not copied

The following reference choices were not imported merely because they exist there:

- Pydantic AI;
- Kitaru;
- Opik;
- Modal;
- Docker SDKs;
- a specific LSP implementation;
- a specific model/provider;
- the reference repository's tool implementation;
- its prompts or agent persona text.

The current project is intentionally dependency-light and provider-neutral. A third-party component should be added only when a concrete requirement, measurable benefit and operational ownership justify it.

## Important licensing boundary

The reference project declares Apache-2.0. Architectural ideas and publicly described design principles were used as research input. No source file from that repository has been copied into this project. If future work imports code, tests, prompts, documentation, or other copyrightable material, perform a license and attribution review first and preserve the applicable notices.

## Next candidates, in priority order

1. **P0/P1: stronger provider-independent tool contract** — represent tool intent, permissions, preconditions, side effects and verification requirements before a host agent executes a tool.
2. **P1: optional LSP capability adapter** — discover installed language servers and use diagnostics only when relevant; never make LSP a hard dependency.
3. **P1: sandbox executor seam** — support explicit `none` / local container / remote executor modes for high-risk autonomous execution, with capability detection and safe fallback.
4. **P1: replay-driven evals** — rerun selected historical task traces against a new routing/context policy and compare outcomes without exposing customer source outside its boundary.
5. **P2: online quality signals** — turn accepted/rejected changes, rework and later regressions into evaluation data while keeping customer data isolated.

The correct strategy is not to turn this project into a clone of the reference course. The useful lesson is architectural discipline: keep the agent core small, put control and quality mechanisms around it, and add each mechanism only when it improves measured engineering outcomes.
