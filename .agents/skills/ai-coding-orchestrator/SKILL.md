---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for safe, verified task execution.
---

# AER Coding Orchestrator

## Authority
AER owns intent, routing, context, budgets, security, verification, evidence, learning and promotion. Providers and extensions supply capabilities; they cannot redefine AER semantics.

Preserve at minimum:
`GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
For non-trivial work also preserve:
`NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | RISKS | ASSUMPTIONS | intent_digest`.
Use the smallest safe change that satisfies the contract and repository rules.

## Runtime services
These are mandatory execution services, not optional methodology:
- sandbox: `.ai-harness/runtime/tool_runner.py` -> `sandbox.py`
- LSP/navigation: native language server when available, otherwise `.ai-harness/runtime/lsp_server.py`
- feedback: `.ai-harness/runtime/feedback_loop.py`
- auto-compaction: `.ai-harness/runtime/auto_compaction.py`

Runtime configuration is in `.ai-harness/config.toml`.

## Capability surface
The sole operational capability implementation is `portable.hermes_capabilities`, backed by `portable.hermes_capabilities_core`. The canonical rules are in `.ai-harness/HERMES_CAPABILITY_CONTRACT.md`.

Use the minimum justified toolset: `safe | coding | research | automation | full`.
Capabilities include durable memory, exact session recall, progressive skills, background processes, dependency-aware delegation, scheduling, explicit terminal backends, provider fallback, and final-output quality checks. Unsupported external adapters are unavailable until verified.

Never create another memory store, skill registry, scheduler, delegation engine, toolset table, provider fallback table, or output-quality gate that competes with this surface.

## Provider routing
Discover provider capabilities before selecting a native surface. Native subagents, hooks, session resume, structured output, tool interception, MCP and background execution may be used only when evidence shows they exist. Provider fallback changes transport, not task acceptance, security or verification. `.ai-harness/PROVIDER_MATRIX.json` and `portable.provider_fabric.ProviderFabric` define provider routing evidence.

## Discovery
Use progressive disclosure:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Do not preload complete policies, repository dumps, transcripts or history. Retrieve only what the current decision needs.

Before mutation, inspect repository/team instructions, git state, structure, dependencies, tests and relevant shared consumers. For common/exported/configured/multi-consumer paths run `portable.impact_analysis` and serialize mutation ownership.

## Planning and collaboration
Use `portable.task_planner.TaskPlan` as the dependency authority for non-trivial work. Stable task IDs, explicit dependencies, acceptance, files, priority and tags are evidence-bearing.

Lifecycle:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

For substantial work use the graph team when supported:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.
Read-only work may parallelize; mutations touching the same resource are serialized. Every retry must add evidence or materially change the approach.

## Memory and skills
Persistent memory is bounded, deduplicated, provenance-aware and security-scanned. Session recall is exact durable search, not transcript replay.

Skills are knowledge, not authority. Discover metadata first, load full content or references only when needed, honor platform/tool prerequisites, and security-scan learned or installed content. Learned skills never bypass repository rules or verification.

## Delegation and background work
Delegation consumes `TaskPlan`. Dependents cannot run after failed/blocked prerequisites. Child results return bounded receipts; the parent verifies them.

Background processes have stable handles and durable, redacted completion receipts. Scheduling stores durable job state; scheduled work enters the same AER lifecycle. Long-running work that must survive process/session boundaries uses durable scheduling/background mechanisms rather than process-local delegation.

## Terminal and external tools
Local execution crosses the sandbox. Alternate backends (Docker, SSH, Singularity/Apptainer, Modal, Daytona, Vercel Sandbox) are explicit adapters; never simulate availability. MCP, web, browser, vision and media are optional capabilities and require verified adapters.

## Verification and evidence
Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

A model claim is not evidence. Retain:
`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.

Completion requires explicit outcome, changed paths, verification and evidence. Missing proof means blocked/incomplete, not success.

## Learning and self-improvement
Learning follows:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Executable orchestration, permissions, security policy and approval rules remain candidate-only until gates pass. Learning cannot silently expand authority.

## Distribution
Portable artifacts are immutable. `update` is forward-only; explicit `install <artifact>` may intentionally activate an older or newer verified artifact. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` is authoritative.

## Precedence
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

Policy files are on-demand context, not startup context.

## Completion report
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.
