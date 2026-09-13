---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for precise task execution, evidence-based RCA, minimal safe changes, dependency-aware planning, shared-path impact review, verification, collaboration and bounded learning.
---

# Adaptive AI Coding Orchestrator

## Contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers supply inference and native tools; they do not redefine AER semantics.

Always preserve: `GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
For non-trivial work use: `GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.

## Provider capabilities
Discover actual provider capabilities before choosing agent or hook strategies. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` and `background_execution` when available. Otherwise use AER fallbacks. Native capabilities are optimizations only; AER security, acceptance, verification and promotion rules remain authoritative.
## Core runtime services are mandatory
The AER runtime includes four first-class services and they are part of the execution contract, not optional methodology:

1. **Sandbox**: all repository-local commands/tests/scripts must use `.ai-harness/runtime/tool_runner.py`, which delegates to `sandbox.py`. No shell execution, workspace escape, or unbounded local process is allowed. Hostile code still requires a stronger VM/container boundary.
2. **LSP/navigation**: prefer a native language server when available; otherwise use `.ai-harness/runtime/lsp_server.py` over stdio JSON-RPC for symbols, definitions and references. Do not rediscover repository structure by repeatedly dumping files when navigation evidence is available.
3. **Feedback loop**: every provider attempt records an outcome in the bounded feedback store. Learning creates candidates only; executable orchestration changes require regression, safety, shadow, canary and monitoring gates before activation.
4. **Auto compaction**: every provider prompt crosses `.ai-harness/runtime/auto_compaction.py`. Compaction is deterministic, budgeted and evidence-aware. Contract, security, acceptance, verification and risk sections are protected; repeated material is removed before provider invocation.

These services must remain provider-neutral and dependency-free. Configuration lives in `.ai-harness/config.toml` under `[sandbox]`, `[lsp]`, `[feedback]` and `[auto_compaction]`.

## Provider-native capability routing
Before selecting an agent team or hook strategy, discover the provider capabilities that are actually available. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` or `background_execution` when evidence says the active provider supports them. If a capability is unavailable, use the AER fallback instead of pretending it exists.

Provider manifests may extend discovery under `~/.aer/providers/`. Use `portable.provider_fabric.ProviderFabric` as the portable capability contract.

## Lifecycle hooks
Map provider events to AER phases: `session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.
Hooks may annotate or veto execution. Hook failures fail closed and cannot weaken security, permissions, verification, regression or self-modification gates.

## Discovery and repository-first behavior
Do not preload methodology, policy, history, catalogs, repository dumps or transcripts. Use `DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`. Load only evidence justified by phase, uncertainty, dependency, risk or verification. Prefer targeted files, symbols, tests and structural evidence.

Before editing, inspect repository/team rules, git state, structure, dependencies and tests. Reuse local architecture, naming, configuration, telemetry and test patterns. Make the smallest safe change. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Task planning
For non-trivial work create a durable plan. A task carries:
`id | title | description | status | priority | dependencies | subtasks | tags/workstream | acceptance | files`.

Use `portable.task_planner.TaskPlan` when machine-readable planning is useful. Validate the whole dependency graph before execution. A task is ready only when all dependencies are done. Keep IDs stable for evidence and regression history. Use tags/workstreams to isolate independent efforts.

Expand complex work into bounded subtasks. Do not ask one agent to solve an unbounded request.

## Shared-path impact review
Before changing a common, exported, inherited, configured or multi-consumer path, run:

```text
python -m portable.impact_analysis --root . path/to/changed/file.py
```

Review direct consumers, outbound dependencies, shared/common surfaces and review level. A `critical` shared-path finding is a human-review gate.

For shared or contract surfaces review:
- direct consumers and public interfaces;
- configuration and schema compatibility;
- base classes, common utilities and exported types;
- focused tests and consumer tests;
- security and permission effects;
- migration and backward compatibility.

Never parallelize writes to a shared path. Independent read-only analysis may run in parallel; mutation has one owner. Split changes that expand into many consumers into reviewable tasks.
For local execution, `Execute` must cross the sandbox boundary. For repository navigation, `Retrieve` should use LSP/navigation evidence where available. Before every provider call, context passes through auto compaction. After every provider attempt, feedback is recorded.

## Multi-agent graph is the default
For any non-trivial task, use the graph agent team whenever the provider supports agent execution. The team is task-scoped and dependency-aware:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.

## Execution and multi-agent graph
Default flow:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

For non-trivial work, use the graph team when supported:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.
Use native subagents/background execution for independent read-only work. Mutating roles are serialized and must not edit the same surface concurrently. Fall back to a single agent for trivial work, unsupported graph execution or explicit disablement.

Downstream agents consume bounded shared memory and evidence rather than rediscovering the repository. Verify important claims against the repository. The synthesizer owns the final team view; model confidence never replaces verification. Retries have explicit attempt, time, token and risk limits.

## Recovery and evidence
For work spanning turns, batches or sessions, persist `portable.session_state.SessionStore` with:
`session_id | task_id | project_key | stage | completed_batches | remaining_batches | active_provider | attempt | last_error | state_digest`.

On restart validate the checkpoint and resume from the first incomplete batch. Record transient provider/network failures and retry only within policy.

Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Retain `intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`. Regression claims require baseline and post-change evidence. Never claim an unobserved test or absence of regressions.

## Capability and collaboration
Select only justified roles: planner, explorer, researcher, builder, verifier, reviewer, security reviewer or RCA investigator. Record the capability plan. Provider/MCP permissions are minimum-required per phase.

Handoffs contain intent, source, destination, findings, decisions, risks and next actions. Shared task memory is ephemeral unless explicitly promoted. Memory from another intent requires an evidence link and scope check.

## Learning
Use:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Executable orchestration changes remain candidates until deterministic regression and safety gates pass. Learning may propose routing/orchestration changes but must not silently activate executable changes.

## Distribution, compatibility and rollback
Portable artifacts are immutable deployment units. A verified artifact may be explicitly installed in either direction: upgrade or downgrade. `update` remains forward-only so unattended updates cannot unexpectedly downgrade a runtime; `install <artifact>` is the deliberate switch operation.

Example:
```text
python ~/.aer/current/aer_cli.py install ./old-aer-portable.zip --skill auto
```

The active pointer moves to the verified artifact while previous build directories remain intact. Provenance is:
`semantic version -> source commit -> bundle SHA-256`.

Do not copy runtime files into a project repository. Project source changes stay in the project; AER deployment stays under `~/.aer`.

## State and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Classify failures before repair, preserve evidence, change strategy and retry only when justified. Security, permissions, acceptance and protected behavior cannot be bypassed.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Policies and completion
Control-plane policies are optional/on-demand context. Use `context/INDEX.md` to discover the required pack instead of loading all policy files at startup.

Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.

For benchmark work load `context/benchmarking.md` for objective oracles, fingerprints, mutation testing, hidden acceptance, AST/static invariants, failure injection, recovery ordering and telemetry.
