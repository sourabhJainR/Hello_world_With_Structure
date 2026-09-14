---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for bounded, evidence-driven execution, verification, collaboration and controlled learning.
---

# Adaptive AI Coding Orchestrator

## Contract
AER owns intent, routing, context selection, budgets, safety, verification, learning and promotion. Providers/extensions supply capabilities but never redefine AER semantics.

Preserve:
`GOAL | BOUNDARIES | ACCEPTANCE | SECURITY/PERMISSIONS | CURRENT STATE`.
For non-trivial work use:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.
Use the minimal safe change consistent with repository rules.

## Provider lifecycle
Discover actual provider capabilities before selecting execution surfaces. Native capabilities may include subagents, hooks, session resume, structured output, tool interception, MCP and background execution, but they cannot override AER security, acceptance, verification or promotion rules.

Map supported provider events to AER phases such as `session_start`, `plan_start`, `before_agent`, `after_agent`, `before_tool`, `after_tool`, `before_verify`, `after_verify`, `before_promotion`, `after_promotion`, `session_end` and `recovery`. Hooks may annotate or veto and must fail closed on handler errors.

## Canonical capability and memory ownership
There is exactly one canonical owner for each cross-cutting capability domain:

- `portable.agent_capabilities` owns the capability catalog, capability risk/fallback semantics, provider adapter selection and durable `PersistentMemory`.
- `portable.capability_fabric` and `portable.persistent_memory` are compatibility facades only.
- `portable.agency_agent_capabilities` owns agency-specific context/tool/event/collaboration metadata only. Its legacy `MemoryStore` is an adapter over canonical `PersistentMemory`; it must not create another durable store.
- New capability or memory behavior must extend the canonical owner first. Do not create another parallel `*Capabilities`, `*MemoryStore`, `*SecondBrain` or provider-specific durable store with overlapping responsibility.

The ownership contract is documented in `docs/CAPABILITY_MEMORY_OWNERSHIP.md`.

## Mandatory runtime services
Sandbox repository-local commands through `.ai-harness/runtime/tool_runner.py` and `sandbox.py`. Prefer native LSP; otherwise use `.ai-harness/runtime/lsp_server.py`. Route every provider attempt through `.ai-harness/runtime/feedback_loop.py`. Route prompts through `.ai-harness/runtime/auto_compaction.py` while preserving contract/security/acceptance/verification/risk content. Configuration lives in `.ai-harness/config.toml`.

## Capabilities
The canonical portable capability implementation is `portable.agent_capabilities`. Discover before use and select the smallest justified capability set. Provider adapters select transport only; AER remains authoritative for acceptance, security and verification. Risky execution requires the sandbox. Scheduled/delegated work re-enters normal lifecycle and cannot bypass policy. Memory is bounded, intent-scoped, redacted and approval-aware. Delegated output is evidence-bearing work, not proof.

## Repository intelligence
Use `portable.repository_intelligence.RepositoryIntelligence` as the single entry point when a task needs repository-wide context.

It composes the existing graph-aware `CodebaseIndex` rather than replacing it, and adds:

- Serena-inspired symbol/relationship retrieval for code understanding;
- stable project-scoped structural context rather than line-number-only addressing;
- Repomix-inspired `.gitignore`/`.ignore`/`.repomixignore` handling;
- secret exclusion before agent context is emitted;
- deterministic token accounting and hard context budgets;
- optional structural compression for broad repository context.

Use semantic retrieval for symbols, references, dependencies and architecture. Use normal text search for strings, comments, configuration and non-code. Use packing only when broad context is justified. Do not make Serena or Repomix runtime dependencies of the core.

## Agency specialist layer
When specialist expertise materially improves a task, use `.agents/skills/agency-specialist-orchestrator/SKILL.md` and the pinned registry when present. Select one primary specialist when possible; add support/review specialists only for independent expertise or material risk. Read-only analysis may be parallel. Mutations are bounded and serialized. Specialist output is work product, never proof by itself.

## Agency Runtime v8
For substantial coding tasks use `portable.ai_coding_agency_bridge` and the v8 skill. It converts the request to a `TaskProfile`, selects specialists, accepts structured worker output, records evidence, evaluates quality, performs artifact regression, records provenance and issues a release decision. The host owns provider/tool calls, permissions, sandboxing, concurrency, mutation ordering and side effects. The bridge never executes commands or grants authority.

A high score is not sufficient for release: hard gates, findings, verification and artifact regression must also pass.

## Agency Runtime v9
For multi-specialist work build a conflict-aware plan with `portable.agency_execution_plan` and expose it through the bridge. Every work unit declares:
`ROLE | MUTATION_MODE | READ_PATHS | WRITE_PATHS | DEPENDENCIES | PRIORITY`.

The host honors plan waves: compatible read-only work may share a wave; overlapping read/write and write/write resources are serialized; independent mutations are explicitly ordered; dependencies precede dependents; missing dependencies or cycles block the plan; undeclared writes are forbidden. Record the execution-plan digest in provenance. Never claim parallelism that the plan did not allow.

## Agency Runtime v10
Repeated coding workflows may pass `BenchmarkHistory` to `run_coding_task` so prior measured outcomes influence the next plan. Each benchmark binds the task to its v9 plan digest and provenance head and records release status, artifact-regression status, quality score, wave/conflict/blocked counts and specialist results.

Adaptive planning is deterministic and bounded. Recent release or regression failures may tighten mutation mode. Frequent conflicts or blocked plans may cap support specialists. Sustained high quality with low conflict may permit one additional support specialist, but never above caller limits. Recommendations never expand permissions, alter protected-path policy, bypass v9 scheduling or convert a failed regression into success. Benchmark history is evidence for future planning, not authorization.

## Control-plane policies
Detailed policies remain on-demand context:
`ORCHESTRATION_SPEC.md | TEN_LOOP_POLICY.md | CONTEXT_POLICY.md | ARCHITECTURE_POLICY.md | EXECUTION_POLICY.md | VERIFICATION_POLICY.md | REVIEW_POLICY.md | LEARNING_POLICY.md | TOKEN_POLICY.md | PROVIDER_CONTRACT.md | QUALITY_GOVERNANCE.md | AGENCY_AGENT_QUALITY.md`.

## Repository-first execution
Use:
`DISCOVER -> SCORE -> LEASE -> USE -> COMPRESS -> RELEASE`.
Inspect instructions, git state, structure, dependencies and tests before editing. Treat undocumented legacy behavior as protected until evidence says otherwise.

## Planning and impact
Use `portable.task_planner.TaskPlan` for durable non-trivial plans. A task is ready only when dependencies are done. Keep IDs stable for evidence and regression history.

Before changing common/exported/inherited/configured/multi-consumer paths run:
`python -m portable.impact_analysis --root . path/to/changed/file.py`.

## Execution, verification and learning
Use:
`Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Impact -> Execute -> Observe -> Evaluate -> Verify -> Review -> Repair -> Learn -> Stop`.

Verification order:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

Retain:
`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.
Regression claims require baseline and post-change evidence.

Learning follows:
`Observe -> Outcome -> Candidate -> Regression Replay -> Safety -> Shadow/Canary -> Promote -> Monitor -> Rollback`.
Executable changes remain candidates until gates pass. Learning must not expand permissions or security boundaries.

## Distribution
Portable artifacts are immutable. `update` is forward-only; explicit `install <artifact>` may activate a verified older/newer artifact. `downgrade=explicit_install_only`. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` is authoritative.

## State and precedence
Engineering State Ledger:
`INTENT | CONTRACT | REPO_FACTS | TASK_PLAN | IMPACT | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

Precedence:
`Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion
Report:
`Outcome | Changed files | Task plan | Impact/shared-path findings | Evidence | Verification | Regression checks | Review | Capability plan | Graph/team execution | Agency specialists | Adaptive recommendation | Benchmark observation | Assumptions | Risks | Incomplete checks | Efficiency`.
