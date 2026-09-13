---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane with capability-aware routing, durable memory, skills, delegation, scheduling, verification and evidence-backed learning.
---

# Adaptive AI Coding Orchestrator

## Contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers and extensions supply capabilities; they do not redefine AER semantics.

Always preserve:
`GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
For non-trivial work use:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.
Use the minimal safe change consistent with this contract and repository rules.

## Unified capability runtime
The task-facing capability implementation is `portable.agent_capabilities`. Public facades are `portable.capability_fabric`, `portable.persistent_memory`, `portable.automation_scheduler` and `portable.output_quality`.

Discover actual capabilities before execution. Use the smallest justified set. Provider adapters select transport only; AER remains authoritative for security, acceptance and verification.

Capability families include provider/model routing, web/X search, browser, terminal/file, vision/media, memory/session recall, progressive-disclosure skills, bounded delegation, durable scheduling/background work, MCP and provider fallback. Risky execution requires the existing sandbox. Scheduled and delegated work re-enters the normal AER lifecycle.

Memory is bounded, project/intent scoped, redacted and approval-aware. Skills are knowledge, not authority. Delegated results are receipts, not proof. Missing evidence blocks a pristine-success claim.

## Provider lifecycle
Discover provider capabilities before choosing execution surfaces. Native subagents, hooks, session resume, structured output, tool interception, MCP and background execution are used only when availability is evidenced. Fallback changes transport, never AER acceptance or security.

Map supported provider events to:
`session_start | plan_start | before_agent | after_agent | before_tool | after_tool | before_verify | after_verify | before_promotion | after_promotion | session_end | recovery`.
Fail closed on policy-handler errors.

## Discovery
Use:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Before editing inspect instructions, git state, structure, dependencies, configuration and tests. Retrieve only evidence justified by the current phase, uncertainty, dependency, risk or verification.

## Planning and collaboration
For non-trivial work use `portable.task_planner.TaskPlan` with stable IDs, dependencies, acceptance and bounded subtasks.

Use the smallest useful team:
`Planner -> Explorer/Researcher/RCA -> Builder -> Verifier -> Independent Reviewers -> Synthesizer`.
Parallelize only independent read-only work. Serialize shared-file mutation. Every delegated attempt has bounded time, tokens, retries, tools and risk.

## Security and mutation
Every tool is risk classified. High-risk actions require approval. Repository-local execution crosses the AER sandbox. MCP, browser and external-system tools use the same permission boundary.

Before changing common/exported/inherited/configured/multi-consumer paths run:
`python -m portable.impact_analysis --root . path/to/changed/file.py`

A critical shared-path finding is a human-review gate.

## Lifecycle
Use:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

## Recovery
Persist session checkpoints for long-running work. Resume from the first incomplete batch and preserve failure evidence. Background work must produce durable bounded receipts; completion must re-enter verification.

## Verification and quality
Use:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

The final `OutputQualityGate` requires acceptance, verification, evidence, clean diff, clean scope and no unresolved findings before reporting ready. Never infer green status from compilation alone.

## Learning
Use:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.

Learning can improve routing, context, skills and workflows but cannot grant permissions or bypass immutable security, acceptance or verification rules.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact findings | Evidence | Verification | Regression checks | Review | Capability plan | Delegation/graph execution | Assumptions | Risks | Incomplete checks | Next actions`.
