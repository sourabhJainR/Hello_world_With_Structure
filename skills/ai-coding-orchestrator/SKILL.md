---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for precise task execution, evidence-based RCA, minimal safe changes, dependency-aware planning, shared-path impact review, verification, collaboration and bounded learning across supported AI coding surfaces.
---

# Adaptive AI Coding Orchestrator

## Provider-neutral contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers supply inference/native tools; they must not redefine AER semantics.

Always active:
`GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
Task contract:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.

## Provider-native capability routing
Before selecting an agent team or hook strategy, discover the provider capabilities that are actually available. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` or `background_execution` when evidence says the active provider supports them. If a capability is unavailable, use the AER fallback instead of pretending it exists.

The portable runtime exposes this contract through `portable.provider_fabric.ProviderFabric`. Provider manifests may extend discovery under `~/.aer/providers/`. Native capability selection is an optimization only; AER security, acceptance, verification and promotion rules remain authoritative.

## Lifecycle hooks
Map provider-native lifecycle events onto AER's hook phases when possible:
`session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.

Hooks may annotate or veto execution. Hook failures are fail-closed. A hook must never silently weaken security, permission, verification, regression or self-modification gates.

## Progressive discovery
Do not preload methodology, policies, frameworks, history, capability catalogs, repository dumps or transcripts. Runtime:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.

The Context Broker loads only evidence justified by phase, uncertainty, dependency, risk or verification. Prefer targeted files/symbols/tests and structural evidence. Release raw context after use. Detailed methodology lives in `context/`; start with `context/INDEX.md` and load only the needed pack. Optional context and extensions are on-demand and must not be treated as always-active.

## Repository-first
Read repository/team instructions, git state, structure, dependencies and tests before editing. Reuse local architecture, naming, configuration, telemetry and test patterns. Make the smallest safe change. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Task planning and dependency discipline
For non-trivial work, create a durable task plan before implementation. A task should carry at least:
`id | title | description | status | priority | dependencies | subtasks | tags/workstream | acceptance | files`.

Use `portable.task_planner.TaskPlan` when a machine-readable plan is useful. Validate the complete dependency graph before execution. Readiness is deterministic: a task is ready only when every dependency is done. Use tags/workstreams to isolate independent efforts without creating separate copies of the same task database.

Prefer:
`PRD/intent -> tasks -> dependency validation -> ready task -> implementation -> verification -> status update`.

Complex tasks should be expanded into smaller subtasks rather than asking one agent to solve an unbounded request. Keep task IDs stable so evidence, work reports and regression history remain traceable.

## Shared-path impact review
Before changing a path that may be common, exported, inherited, configured, or consumed by multiple components, run deterministic impact analysis:

```text
python -m portable.impact_analysis --root . path/to/changed/file.py
```

The analyzer identifies direct changes, inbound consumers, outbound dependencies, shared/common surfaces and a review level. Treat `critical` shared-path findings as a human-review gate.

For shared or contract surfaces, review at least:
- all direct consumers and public interfaces;
- configuration and schema compatibility;
- base classes, common utilities and exported types;
- focused tests plus consumer tests;
- security and permission effects;
- migration/backward-compatibility requirements.

Do not parallelize writes to a shared path. Independent read-only analysis may run in parallel, then a single builder owns the mutation. A change that expands into many consumers should be split into reviewable tasks before implementation.

## Execution
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact analysis -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

## Multi-agent graph is the default
For any non-trivial task, use the graph agent team whenever the provider supports agent execution. The team is task-scoped and dependency-aware:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.

When native subagents/background execution are available, prefer them for independent read-only work. Keep shared task memory bounded and evidence-based. Mutating roles are serialized and must not edit the same surface concurrently. A single-agent phase is the fallback only when the graph team is unavailable, unnecessary for a trivial task, or explicitly disabled.

Do not create disconnected sub-agents that independently rediscover the repository. Downstream agents must consume upstream shared memory and verify important claims against the repository. The synthesizer is responsible for the final team view; model confidence never replaces verification.

Every retry has explicit attempt/time/token/risk limits. Never run an unrestricted autonomous loop.

## Durable recovery
For work spanning multiple turns, batches or sessions, persist a checkpoint using `portable.session_state.SessionStore`. The checkpoint must include `session_id | task_id | project_key | stage | completed_batches | remaining_batches | active_provider | attempt | last_error | state_digest`.

On restart, load and validate the checkpoint before doing new work. Resume from the first incomplete batch. After transient provider/network failure, record the error, retry within the bounded policy, and continue from the durable checkpoint rather than reconstructing state from chat history.

## Evidence and verification
Verification outranks model confidence. Use:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Retain `intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`. A regression requires baseline/post evidence. Never claim tests, commands or absence of regressions that were not observed.

## Capability and collaboration
Select only justified roles: planner, explorer, researcher, builder, verifier, reviewer, security reviewer or RCA investigator. Record the capability plan. Provider/MCP permissions are minimum-required per phase. Handoffs contain intent, source, destination, findings, decisions, risks and next actions.

Shared task memory is ephemeral to the active run unless explicitly promoted into durable learning. Memory from another intent must never be injected into the current task without an explicit evidence link and scope check.

## Learning
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Executable orchestration changes remain candidates until deterministic regression and safety gates pass. A learning engine may propose changes to orchestration or provider routing, but it must not silently activate executable changes. Load `context/learning.md` only when learning/self-improvement is relevant.

## Distribution, compatibility and rollback
Portable artifacts are immutable deployment units. A verified artifact may be installed explicitly in either direction: upgrade or downgrade. `update` remains forward-only so an unattended update cannot unexpectedly downgrade a runtime; `install <artifact>` is the deliberate switch operation and may activate an older pinned build.

Use:
```text
python ~/.aer/current/aer_cli.py install ./old-aer-portable.zip --skill auto
```

The active pointer moves atomically to the verified artifact while previous build directories remain intact. The provenance chain remains:
`semantic version -> source commit -> bundle SHA-256`.

Do not copy runtime files into a project repository. Project source changes belong to the project; AER deployment belongs under `~/.aer`.

## State, recovery and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Classify failure before repair, preserve evidence, change strategy and retry only when justified. Security, permissions, acceptance and protected behavior cannot be bypassed.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Control-plane policies
Policy files are optional/on-demand context, not startup context. The complete control-plane contract is defined by: `ORCHESTRATION_SPEC.md | TEN_LOOP_POLICY.md | CONTEXT_POLICY.md | ARCHITECTURE_POLICY.md | EXECUTION_POLICY.md | VERIFICATION_POLICY.md | REVIEW_POLICY.md | LEARNING_POLICY.md | TOKEN_POLICY.md | PROVIDER_CONTRACT.md | QUALITY_GOVERNANCE.md`.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.

For benchmark work load `context/benchmarking.md`, which defines independent objective oracles, fingerprints, mutation testing, hidden acceptance, AST/static invariants, deterministic failure injection, recovery ordering, Context Broker telemetry and separate observability scoring.
