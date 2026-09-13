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
Use the minimal safe change consistent with this contract and the repository rules.

## Provider capabilities and lifecycle
Discover actual provider capabilities before choosing execution surfaces. Prefer native `subagent`, `hooks`, `session_resume`, `structured_output`, `tool_interception`, `mcp` and `background_execution` only when evidence shows they are available; otherwise use AER fallbacks. Native capability selection cannot override AER security, acceptance, verification or promotion rules.

Map provider events to AER phases when supported:
`session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.
Hooks may annotate or veto execution and fail closed on handler errors.
Provider manifests may extend discovery under `~/.aer/providers/`; `portable.provider_fabric.ProviderFabric` is the portable capability contract.

## Mandatory runtime services
These are execution services, not optional methodology:

1. Sandbox: repository-local commands/tests/scripts cross `.ai-harness/runtime/tool_runner.py`, which delegates to `sandbox.py`.
2. LSP/navigation: prefer a native language server; otherwise use `.ai-harness/runtime/lsp_server.py`.
3. Feedback: every provider attempt crosses `.ai-harness/runtime/feedback_loop.py`; learning creates candidates only.
4. Auto compaction: every provider prompt crosses `.ai-harness/runtime/auto_compaction.py`; protected contract/security/acceptance/verification/risk content is preserved.

Configuration lives in `.ai-harness/config.toml`.

## Unified capability runtime
The task-facing capability implementation is `portable.agent_capabilities`. Public facades are `portable.capability_fabric`, `portable.persistent_memory`, `portable.automation_scheduler` and `portable.output_quality`.

Use the smallest justified capability set. Discover first; do not assume external adapters exist. Provider adapters select transport only; AER remains the authority for acceptance, security and verification.

Capability families include web/X search, browser, terminal/file, vision/media, memory/session recall, skills, task delegation, scheduling/background work, MCP and provider fallback. Risky execution requires the existing sandbox. Scheduled and delegated work re-enters the normal AER lifecycle and cannot bypass policy.

Memory is bounded, project/intent scoped, redacted and approval-aware. Skills use progressive disclosure and prerequisite checks. Delegated results are receipts, not proof. Missing evidence blocks a pristine-success claim.

The final `OutputQualityGate` requires acceptance, verification, evidence, clean diff, clean scope and no unresolved findings before reporting ready.

## Control-plane policies
Detailed policies remain on-demand context. Use:
`ORCHESTRATION_SPEC.md | TEN_LOOP_POLICY.md | CONTEXT_POLICY.md | ARCHITECTURE_POLICY.md | EXECUTION_POLICY.md | VERIFICATION_POLICY.md | REVIEW_POLICY.md | LEARNING_POLICY.md | TOKEN_POLICY.md | PROVIDER_CONTRACT.md | QUALITY_GOVERNANCE.md`.

## Discovery and repository-first
Use:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Load only evidence justified by phase, uncertainty, dependency, risk or verification. Before editing inspect instructions, git state, structure, dependencies and tests. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Task planning
For non-trivial work create a durable dependency-aware plan with `portable.task_planner.TaskPlan` when machine-readable planning is useful. A task is ready only when every dependency is `done`. Keep IDs stable for evidence and regression history.

## Impact and mutation boundaries
Before changing common/exported/inherited/configured/multi-consumer paths run:
`python -m portable.impact_analysis --root . path/to/changed/file.py`

Independent read-only analysis may run in parallel. Mutations are serialized; one owner edits a shared path.

## Execution and graph collaboration
Use:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

For non-trivial tasks use:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.
Read-only roles may run in parallel; mutating roles are serialized. Every retry has explicit attempt, time, token and risk limits.

## Recovery and evidence
Persist `portable.session_state.SessionStore` for work spanning turns/batches. On restart resume from the first incomplete batch and preserve failure evidence.

Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Retain:
`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.
Regression claims require baseline and post-change evidence.

## Learning
Use:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.
Executable orchestration changes remain candidates until gates pass. Learning must not expand permissions or security boundaries.

## Distribution
Portable artifacts are immutable. `update` is forward-only; explicit `install <artifact>` may activate an older/newer verified artifact. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` is authoritative.

## State and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.
