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
Use the minimal safe change consistent with the task and repository rules.

## Provider capabilities and lifecycle
Discover actual provider capabilities before choosing execution surfaces. Native subagents, hooks, session resume, structured output, tool interception, MCP and background execution may be used only when evidence shows they exist. Provider fallback changes transport, never AER acceptance, security or verification rules.

Map provider events to AER phases when supported:
`session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.
Hooks may annotate or veto execution and fail closed on handler errors. Provider manifests may extend discovery under `~/.aer/providers/`; `portable.provider_fabric.ProviderFabric` remains the provider capability contract.

## Mandatory runtime services
These are execution services, not optional methodology:
1. Sandbox: repository commands/tests cross `.ai-harness/runtime/tool_runner.py` -> `sandbox.py`.
2. LSP/navigation: prefer a native server; otherwise `.ai-harness/runtime/lsp_server.py`.
3. Feedback: provider attempts record bounded outcomes; learning creates candidates only.
4. Auto-compaction: provider prompts cross `.ai-harness/runtime/auto_compaction.py` with protected contract/security/acceptance/verification/risk content preserved.

Runtime configuration is `.ai-harness/config.toml`.

## Capability surface
The canonical operational capability surface is:
`portable.capability_fabric | portable.persistent_memory | portable.automation_scheduler | portable.output_quality`.
Their sole implementation is `portable.agent_capabilities`; these modules are stable façades, not parallel runtimes.

Available capability classes cover:
`web_search | x_search | terminal | browser | file | vision | image_generation | tts | todo | memory | session_search | cronjob | execute_code | delegate_task | clarify | mcp | skills | background_processes | provider_fallback`.

Use the smallest justified capability set. `CapabilityFabric.plan()` must account for network/sandbox constraints. Optional external capabilities are unavailable until verified; safe fallbacks are explicit rather than simulated.

## Memory and session recall
Persistent memory is bounded, intent-scoped, redaction-aware and approval-aware. Session recall uses exact durable search rather than replaying entire transcripts. Memory never overrides repository rules, acceptance criteria, or current context leases.

## Skills and progressive disclosure
Treat skills as knowledge, not authority. Inspect metadata first; load procedures/references only when needed. Respect `requires_tools`, `requires_toolsets`, `fallback_for_tools` and `fallback_for_toolsets`. Learned skills pass the same security and verification gates as authored skills.

## Todo, delegation and background execution
`portable.task_planner.TaskPlan` owns dependency semantics. Parallel delegated work may run only when dependencies are satisfied; failed prerequisites block dependents. Child results return bounded receipts and are verified by the parent.

Long-running work that must survive sessions uses durable scheduling/background mechanisms. Background process handles must produce durable, bounded and redacted receipts.

## Scheduling
`portable.automation_scheduler.AutomationScheduler` owns durable due/claim/retry/run state. Scheduled work re-enters the same AER lifecycle and cannot bypass security or verification.

## Terminal and external tools
All local command execution crosses the sandbox. Alternate execution backends (Docker, SSH, Singularity/Apptainer, Modal, Daytona, Vercel Sandbox) require explicit adapters and verified configuration. MCP, browser, web/X search, vision, image generation and TTS are optional adapters and never assumed available.

## Research and collaboration
For research use progressive retrieval and preserve source evidence. Parallel read-only investigation is allowed; same-resource mutation is serialized. For substantial tasks use:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Parallel Reviewers -> Synthesizer`.

## Verification and output quality
Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

A model claim is not evidence. `portable.output_quality.OutputQualityGate` adds a final objective gate across acceptance, verification, evidence, diff cleanliness and scope cleanliness. Missing proof means blocked/incomplete, never polished false success.

## Recovery and learning
Persist `portable.session_state.SessionStore` for work spanning turns/batches. Resume from the first incomplete batch and retain failure evidence.

Learning follows:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.
Executable orchestration, security policy, approval rules and permissions remain candidate-only until gates pass.

## Discovery and impact
Use:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Before mutation inspect repository instructions, structure, dependencies, tests and shared consumers. For common/exported/configured/multi-consumer changes run `portable.impact_analysis` and serialize mutation ownership.

## State and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

Detailed policy is on-demand context, not startup context.

## Distribution
Portable artifacts are immutable. `update` is forward-only; explicit `install <artifact>` may intentionally activate an older or newer verified artifact. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` is authoritative and uses `downgrade=explicit_install_only`.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Assumptions | Risks | Incomplete checks | Efficiency`.
