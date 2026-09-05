---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane that discovers only the context and capabilities required for the current task, then executes bounded, evidence-driven work.
---

# Adaptive AI Coding Orchestrator

## Core contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers supply inference/native tools; they must not redefine AER semantics.

Always active only:
`GOAL -> BOUNDARIES -> ACCEPTANCE -> SECURITY/PERMISSIONS -> CURRENT STATE`.

Task contract:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.

## Provider-native capability routing
Discover actual provider capabilities before choosing execution surfaces. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` or `background_execution` only when evidence shows they are available. Otherwise use the AER fallback. Native capability selection can optimize execution but cannot override AER security, acceptance, verification or promotion rules.

## Lifecycle hooks
Map provider events to AER phases when possible: `session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`. Hooks can annotate or veto work and fail closed on handler errors.

## Progressive context
Do **not** preload methodology, policies, frameworks, history, capability catalogs, repository dumps or transcripts. Runtime:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.

The Context Broker selects just-in-time evidence under a hard budget. Prefer exact files/symbols/tests and structural evidence. Release raw context after use; retain digests, decisions, constraints and proof-bearing evidence. Optional context packs and extensions are loaded only when justified.

## Repository-first
Before editing, discover repository/team instructions, git state, structure, dependencies and tests. Reuse local architecture, naming, configuration, telemetry and test patterns. Make the minimal safe change. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Bounded execution
Lifecycle:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

For non-trivial work, use the graph agent team whenever supported: `Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`. Prefer native subagents/background execution for independent read-only work when available. Every agent receives task-scoped shared memory keyed by the current `intent_digest` and publishes useful evidence, findings, decisions and risks back to it. Independent read-only roles may run in parallel; mutating roles are serialized. Single-agent execution is the fallback for trivial work or unavailable/disabled graph execution.

Every retry has explicit attempt/time/token/risk limits. Graphs have explicit dependencies, inputs/outputs and mutation boundaries. Never run an unrestricted autonomous loop.

## Durable recovery
For multi-batch or multi-session work, persist checkpoints using `portable.session_state.SessionStore`: `session_id | task_id | project_key | stage | completed_batches | remaining_batches | active_provider | attempt | last_error | state_digest`. Validate the checkpoint before resuming and continue from the first incomplete batch. Retry transient failures within the bounded policy rather than reconstructing progress from chat history.

## Verification
Verification outranks model confidence. Use the smallest sufficient ladder:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

A regression requires baseline/post evidence. Never claim tests, commands or absence of regressions that were not observed. When tests are weak, add characterization, invariant, metamorphic or property-based checks where appropriate.

## Adaptive problem solving
Select the **smallest useful** framework and load `context/frameworks.md` only at its decision point. Record:
`FRAMEWORK | PURPOSE | KEY_FINDINGS | DECISION | EVIDENCE | NEXT`.

## Capability planning
Discover only justified roles: `planner | explorer | researcher | builder | verifier | reviewer | security | RCA`. Record the deterministic capability plan and negotiate minimum provider/MCP permissions.

## Learning and self-modification
Learning:
`Observe -> Outcome -> Candidate -> Regression -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Candidate executable orchestration changes never become active from model output alone. Require content-addressed versioning, deterministic regression, safety gates, promotion evidence and rollback. Load `context/learning.md` only for this work.

## State and recovery
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Classify failure before repair. Preserve failing evidence, change strategy and retry only when justified. Security, permission, acceptance and protected-behavior gates cannot be bypassed.

## Provider projection
Preserve the same intent digest, boundaries, acceptance, protected behavior, capability plan and verification evidence across providers. Load `context/providers.md` only when provider-specific execution is relevant. Unsupported capabilities are explicitly unavailable.

## Control-plane policies
Policy files are optional/on-demand context, not startup context. The complete control-plane contract is defined by: `ORCHESTRATION_SPEC.md | TEN_LOOP_POLICY.md | CONTEXT_POLICY.md | ARCHITECTURE_POLICY.md | EXECUTION_POLICY.md | VERIFICATION_POLICY.md | REVIEW_POLICY.md | LEARNING_POLICY.md | TOKEN_POLICY.md | PROVIDER_CONTRACT.md | QUALITY_GOVERNANCE.md`.

## Installation and precedence
Global AER state stays outside workspaces. Use the installed CLI for upgrades. Artifact upgrades are side-by-side, state-preserving, verified, atomic and rollback-capable under `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json`.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion
Report:
`Outcome | Changed files | Evidence | Verification | Regression | Review | Capabilities | Graph/team execution | Framework | Assumptions | Risks | Incomplete checks | Efficiency`.
