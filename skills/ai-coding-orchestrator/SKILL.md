---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for bounded, evidence-driven task execution, dependency-aware planning, impact review, verification, collaboration and controlled learning.
---

# Adaptive AI Coding Orchestrator

## Contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers and extensions supply capabilities; they do not redefine AER semantics.

Always preserve:
`GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
For non-trivial work use:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.
Use the **minimal safe change** consistent with this contract and the repository rules.

## Provider capabilities and lifecycle
Discover actual provider capabilities before choosing execution surfaces. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` and `background_execution` only when evidence shows they are available; otherwise use AER fallbacks. Native capability selection cannot override AER security, acceptance, verification or promotion rules.

Map provider events to AER phases when supported:
`session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.
Hooks may annotate or veto execution and fail closed on handler errors.
Provider manifests may extend discovery under `~/.aer/providers/`; `portable.provider_fabric.ProviderFabric` is the portable capability contract.

## Mandatory runtime services
These are execution services, not optional methodology:

1. **Sandbox**: repository-local commands/tests/scripts cross `.ai-harness/runtime/tool_runner.py`, which delegates to `sandbox.py`.
2. **LSP/navigation**: prefer a native language server; otherwise use `.ai-harness/runtime/lsp_server.py` for symbols, definitions and references.
3. **Feedback**: every provider attempt crosses `.ai-harness/runtime/feedback_loop.py` and records bounded outcome data; learning produces candidates only.
4. **Auto compaction**: every provider prompt crosses `.ai-harness/runtime/auto_compaction.py`; protected contract, security, acceptance, verification and risk content is preserved.

Configuration lives in `.ai-harness/config.toml` under `[providers]`, `[execution]`, `[capabilities]`, `[terminal]`, `[sandbox]`, `[lsp]`, `[feedback]`, `[auto_compaction]`, `[orchestration]`, `[learning]`, `[router]`, `[context]` and `[workflows]`.

## Capability contract
Use `.ai-harness/HERMES_CAPABILITY_CONTRACT.md` and `portable.hermes_capabilities` as the single operational capability surface. Do not create alternative memory, skill, process, scheduler, delegation, toolset or quality-gate implementations.

For non-trivial work, discover capabilities first, select the minimum justified toolset, and record the choice in the task evidence. The standard presets are `safe`, `coding`, `research`, `automation` and `full`; `full` still obeys every capability-level security and verification gate.

Persistent memory is bounded, deduplicated and security-scanned. Session recall uses exact durable search. Skills are progressive-disclosure knowledge and are not executable authority. Delegation must consume `TaskPlan`; dependent tasks wait for prerequisites. Background work produces durable redacted receipts. Scheduled work re-enters the same AER state machine. External terminal backends are unavailable until explicitly configured and verified. Provider fallback changes transport, never acceptance or verification rules.

## Control-plane policies
The skill is the routing entry point; detailed policies remain separate and are discovered on demand. The control-plane set is:
`ORCHESTRATION_SPEC.md | TEN_LOOP_POLICY.md | CONTEXT_POLICY.md | ARCHITECTURE_POLICY.md | EXECUTION_POLICY.md | VERIFICATION_POLICY.md | REVIEW_POLICY.md | LEARNING_POLICY.md | TOKEN_POLICY.md | PROVIDER_CONTRACT.md | QUALITY_GOVERNANCE.md | HERMES_CAPABILITY_CONTRACT.md`.

These policy files refine execution but cannot override the precedence order defined below.

## Discovery and repository-first
Do not preload full methodology, policies, history, catalogs, repository dumps or transcripts. Use:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Load only evidence justified by phase, uncertainty, dependency, risk or verification. Prefer targeted files, symbols and tests.

Before editing, inspect repository/team instructions, git state, structure, dependencies and tests. Reuse local architecture, naming, configuration and telemetry. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Task planning
For non-trivial work create a durable, dependency-aware plan using `portable.task_planner.TaskPlan` when machine-readable planning is useful. Each task uses:
`id | title | description | status | priority | dependencies | subtasks | tags | acceptance | files`.

Validate the whole dependency graph before execution. A task is ready only when every dependency is `done`. Keep IDs stable for evidence and regression history. Use tags to isolate workstreams. Keep subtasks bounded.

## Impact and mutation boundaries
Before changing a common, exported, inherited, configured or multi-consumer path, run:
```text
python -m portable.impact_analysis --root . path/to/changed/file.py
```

Review direct consumers, outbound dependencies, shared/common surfaces, compatibility, configuration, security effects and suggested tests. A `critical` shared-path finding is a human-review gate.

Independent read-only analysis may run in parallel. Mutations are serialized; one owner edits a shared path.

## Execution and graph collaboration
Use the lifecycle:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

For non-trivial tasks, use the graph team whenever supported:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.

Downstream agents consume bounded shared memory and repository evidence rather than rediscovering the same work. Read-only roles may run in parallel; mutating roles are serialized. Single-agent execution is the fallback for trivial work or unavailable/disabled graph execution. Every retry has explicit attempt, time, token and risk limits.

For local execution, `Execute` must cross the sandbox boundary. Before every provider call, context crosses auto compaction. After every provider attempt, feedback is recorded. Provider-native capabilities optimize execution; harness-owned acceptance, security and verification remain authoritative.

## Recovery and evidence
For work spanning turns, batches or sessions, persist `portable.session_state.SessionStore` with:
`session_id | task_id | project_key | stage | completed_batches | remaining_batches | active_provider | attempt | last_error | state_digest`.

On restart validate the checkpoint and resume from the first incomplete batch. Preserve failure evidence and change strategy before retrying.

Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Retain:
`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.
Regression claims require baseline and post-change evidence.

## Capability, collaboration and learning
Select only justified roles: `planner | explorer | researcher | builder | verifier | reviewer | security | RCA`.
Record the capability plan and minimum provider/MCP permissions. Handoffs contain intent, source, destination, findings, risks and next actions.

Shared task memory is scoped to the current `intent_digest`. Cross-intent memory requires an evidence link and scope check.

Learning follows:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.
Executable orchestration changes remain candidates until deterministic regression, safety and promotion gates pass. Learning must not silently expand permissions or security boundaries.

## Distribution and compatibility
Portable artifacts are immutable deployment units. `update` is forward-only. `install <artifact>` is the deliberate operation that may explicitly switch to an older or newer verified artifact. Previous immutable build directories remain intact.

The authoritative artifact policy is `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json`; its `downgrade=explicit_install_only` semantics must match the CLI.

Do not copy runtime files into a project repository. Project source stays in the project; AER deployment stays under `~/.aer`.
Provenance is:
`semantic version -> source commit -> bundle SHA-256`.

## State and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

Policy files are on-demand context, not startup context. Discover them through the repository's control-plane index rather than loading the full policy set.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.
