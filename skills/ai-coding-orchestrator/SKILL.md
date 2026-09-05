---
name: ai-coding-orchestrator
description: Repository-aware AI engineering control plane for precise task execution, evidence-based RCA, graph orchestration, bounded agent loops, gated self-modification, verification, collaboration and evidence-driven learning.
---

# Adaptive AI Coding Orchestrator

Lifecycle: `Understand -> Profile -> Specify -> Retrieve -> Route -> Capability plan -> Plan -> Execute -> Observe -> Evaluate -> Graph join -> Verify -> Review -> Repair if justified -> Learn -> Self-modify -> Regression -> Safety -> Shadow -> Canary -> Promote -> Monitor -> Rollback -> Stop`.

Normal mode is one bounded adaptive run. Never create an unrestricted autonomous loop. Repetition must have an explicit budget, measurable acceptance criteria and an evaluation gate.

## Existing-install migration

This skill is versioned with AER and is part of the portable distribution. If a machine was installed from an earlier AER artifact, do not manually copy the new skill or runtime into a repository.

Upgrade the machine-scoped installation using the installed CLI:

```bash
python ~/.aer/current/aer_cli.py check-update --ref main
python ~/.aer/current/aer_cli.py update --ref main
```

After update, verify the active installation and reload the coding-agent integration if required by the provider. Existing AER installations must not mix files from different AER versions. The updater is responsible for installing the new pinned bundle and switching the user-level `current` pointer atomically.

The new orchestration behavior is active only after the updated AER version is installed. Repository source files are not modified by the migration.

## Portable isolation

AER is machine-scoped when installed globally. The current repository is a workspace, never the AER installation directory.

- Never vendor AER implementation, runtime, policy, cache, journal, telemetry, learning or regression files into a workspace merely to use AER.
- Never modify `.git`, hooks, remotes, ignore files, permissions, MCP configuration, credentials or external agent configuration as part of normal AER use.
- Keep AER runtime, immutable policies, regression corpus, learned machine state, journals and caches outside the repository unless the user explicitly requests repository-local AER artifacts.
- Repository changes are limited to the engineering work the user requested; installation itself is zero-mutation to the repository.

## Task contract

Create or load a protected contract:
`GOAL | NON-GOALS | REQUIREMENTS | CONSTRAINTS | PROTECTED BEHAVIOR | BOUNDARIES | ACCEPTANCE | RISKS | ASSUMPTIONS | intent_digest`.

Carry the intent digest through phases, graph nodes, retries, resumes and handoffs. Challenge ambiguity when it materially affects correctness, safety, architecture, scope or verification; otherwise state assumptions and continue.

For short or informal requests, infer the smallest missing engineering contract rather than expanding scope. Explicitly preserve desired behavior and motivation; retain environment/reproduction details when they materially affect execution or verification.

## Repository-first engineering

Read repository/team instructions, git state, structure, dependencies and tests before editing. Reuse local architecture, naming, placement, exception handling, logging, telemetry, DI, configuration and test patterns. Make the smallest safe change. Do not add speculative abstractions, unrelated cleanup or silent dependencies.

Treat undocumented legacy behavior as protected until evidence says otherwise. Trace callers, branches, feature/config gates, persistence, integrations, failure paths and data shapes. Prefer characterization tests and seam-level compatibility changes over rewrites.

Apply proportionally: DRY, YAGNI, KISS, SOLID, dependency inversion, high cohesion/low coupling, composition, least surprise, least privilege, locality of change, observability, reversibility and evidence over assumption.

## Graph orchestration

AER uses four distinct levels of control:

`Agent -> bounded Loop -> Graph -> Orchestration`

- **Agent:** performs a focused capability such as exploration, implementation, verification or review.
- **Bounded loop:** allows `Plan -> Act -> Observe -> Evaluate` to repeat only within explicit attempt, time, token and risk budgets.
- **Graph:** represents dependencies, joins, gates, routing and ordering between capabilities. Independent read-only nodes may run in parallel; conflicting writes never run concurrently.
- **Orchestration:** governs the complete workflow, contracts, budgets, evidence, policy, verification, recovery, learning and lifecycle.

Every executable graph node has a stable identity, declared inputs/outputs, dependency set, risk class and evaluation gate. Graphs must be acyclic unless a loop is explicitly represented as a bounded retry/repair construct with a hard budget.

The orchestrator must:

1. Establish the task contract and `intent_digest`.
2. Profile repository state, execution environment and collect authoritative evidence.
3. Build a capability plan and dependency-aware execution graph.
4. Execute eligible nodes only when their dependencies and policy gates pass.
5. Record observations, trajectory and proof-bearing evidence after meaningful actions.
6. Evaluate outcomes before allowing graph progress.
7. Repair only when the failure is actionable and the repair has a bounded budget.
8. Re-evaluate after repair; never retry blindly.
9. Join graph branches only after required branch gates pass.
10. Verify acceptance, regression paths and final changes before completion.
11. Record outcome, open risks and unresolved checks in the state ledger.
12. Emit a learning signal/candidate from evidence and trajectory rather than trusting a single successful run.

Evaluation is a first-class control point, not a final report. A failed evaluator blocks dependent graph nodes unless an explicit recovery path permits progress.

## Evidence-driven agent engineering

Treat the agent plus harness as the system under evaluation. Do not optimize only for model confidence or one-shot pass rate. Current coding-agent research increasingly evaluates repository understanding, validation, maintenance, long-horizon evolution, realistic requests and execution environments rather than code generation alone. citeturn0academia54turn0academia29turn0search3turn0search9

For each meaningful run retain:

`intent_digest | graph_digest | environment_fingerprint | trajectory | attempts | repairs | evaluator outcomes | evidence digests | final outcome`.

Use these records to distinguish model failure from retrieval, environment, state, tool, verification or orchestration failure. Make the harness observable and auditable; sandboxing, constrained execution, explicit approvals for higher-risk actions and agent-native telemetry are practical reliability controls. citeturn0search0turn0search2

Prefer continuous engineering evaluation over a static benchmark mentality. Re-run representative tasks against the evolving repository and track:

- acceptance/pass rate
- regression rate
- repair rate
- attempts/tool calls per accepted task
- verification coverage
- token/latency/cost efficiency when available
- forgetting on previously solved cases
- forward transfer to related tasks
- backward transfer to older tasks
- environment/tool failure rate

Do not declare an improvement from one task. Require repeated evidence across representative task families where practical. Continual-learning work specifically recommends measuring accuracy, forgetting, forward/backward transfer and tool-use efficiency rather than only aggregate task success. citeturn0academia27

## Benchmark and regression discipline

Use multiple evaluation classes rather than one benchmark:

1. repository-native unit/integration/system tests
2. deterministic regression replay
3. realistic issue-style tasks
4. refactoring/maintenance tasks
5. test-writing and verification tasks
6. long-horizon CI/evolution tasks
7. domain-specific tasks when correctness depends on specialized knowledge

Use rolling or contamination-resistant task sets where possible. Current benchmark work is moving toward continuously refreshed tasks, trajectory checks, realistic user requests and large-scale refactoring/maintenance because static issue resolution can hide important weaknesses. citeturn0search1turn0academia55turn0academia56turn0search6

Keep benchmark fixtures and expected outcomes isolated from candidate implementation. Do not expose hidden answers, gold patches or evaluation results to the agent. Preserve rollout/trajectory evidence so evaluation can detect leakage or accidental benchmark contamination.

When tests may be incomplete, add characterization, invariant, metamorphic or property-based checks where appropriate. A passing narrow test is not sufficient evidence of general correctness.

## Capability planning and collaboration

Before provider execution, use the deterministic capability catalog and record `capability-plan.json`. Select only justified roles: planner, explorer, researcher, builder, verifier, reviewer, security reviewer or RCA investigator.

Parallelize only independent read-only work; never parallelize edits to the same file or shared mutable state. Meaningful handoffs contain `intent_digest + source + destination + phase + findings + decisions + open risks + next actions`. Validate intent and scope before consuming a handoff.

## RCA mode

For RCA, diagnosis or investigation without an explicit fix request: do not edit, commit, push or patch. Trace the real call/data flow, inspect source/tests/history/logs/persistence/integrations, compare data shapes, classify `Fact | Inference | Unknown | Recommendation`, attach evidence and report root cause as `proven | probable | unproven`.

A later regression links to the original run and intent and becomes a learning event, not an unsolicited patch.

## Verification and quality

Verification outranks model confidence. Check acceptance, relevant regression paths, final diff and repository-native validation. Never claim tests, commands or absence of regressions that were not observed.

Use layered verification for meaningful changes: syntax/static checks -> focused tests -> integration/system checks -> regression replay -> security/policy checks -> final diff review.

For self-modifying candidates, static validation must not execute generated code. Candidate behavior is exercised only inside the designated isolated regression/safety evaluation boundary. This separates candidate generation from candidate execution and prevents inspection itself from becoming an execution path. 

Review architecture boundaries, coupling, lifecycle/compatibility, failure handling, security, observability, timeout/retry/cancellation/idempotency, configuration and rollout/rollback when relevant.

## Execution, loops and durability

Split substantial work into independently verifiable graph nodes. Checkpoint meaningful phases/chunks and re-anchor on context rot, instruction loss, intent drift, scope drift or contradiction.

Use the loop sequence:

`Generation -> Evaluation -> Memory -> Scheduling -> Optimization`

Within an executable task loop, use:

`Plan -> Act -> Observe -> Evaluate -> Repair? -> Re-evaluate`

Every retry must add evidence, change strategy or both. Stop when acceptance is met, the budget is exhausted, evidence stops improving, risk becomes unacceptable or no justified next action remains.

Runtime events remain in the external AER state location by default. Repository-specific work products are separate from AER machine state unless the user explicitly requests repository-local artifacts.

## Context economics

Treat the repository as structured evidence. Prefer repository rules/acceptance, AST/symbol/dependency structure, graph impact paths, exact search, semantic retrieval when configured, targeted reads, then verification output.

Use optional code-intelligence extensions only when available, relevant and permitted. Keep stable context small, rank evidence, compact history by information value, preserve proof-bearing state, reuse summaries and avoid transcript replay. Optimize verified outcome per token, call, retry and latency.

When a task is underspecified, ask for or infer desired behavior and motivation before expanding context. Prefer targeted evidence over indiscriminate repository ingestion; recent empirical work finds realistic short requests materially harder than benchmark-style prompts and shows desired behavior/motivation can improve resolution. citeturn0academia55

## Engineering State Ledger

For non-trivial work maintain:
`INTENT | CONTRACT | REPO_FACTS | DECISIONS | EVIDENCE | CHANGESET | VERIFY | OUTCOME | OPEN_RISKS | NEXT`.

For graph execution also retain node status and gate evidence: `READY | RUNNING | PASSED | FAILED | BLOCKED | SKIPPED`.

For self-modification retain `CANDIDATE_ID | PARENT_DIGEST | SOURCE_DIGEST | REGRESSION | SAFETY | PROMOTION | ACTIVE_VERSION | ROLLBACK_TARGET`.

Material decisions reference evidence. Verification identifies proof. Outcome records accepted/rejected/partial results, review/production feedback, regressions and metrics. Replay must preserve the original `intent_digest` and relevant evidence references.

## Regression replay

A regression is a durable learning signal. When a change, repair or learned strategy is evaluated:

1. Capture the baseline outcome and relevant evidence.
2. Add or reference a deterministic regression case when the failure is reusable.
3. Replay the case against the candidate behavior.
4. Compare expected acceptance, safety and compatibility outcomes.
5. Reject candidates that introduce known regressions or weaken protected behavior.
6. Where tests are weak, add invariant/metamorphic/property checks before treating the candidate as verified.
7. Only then allow safety evaluation and shadow/canary evaluation.

Replay should be deterministic where the underlying test permits it. Nondeterministic tests must expose their uncertainty rather than being treated as clean passes.

## Learning and self-improvement

Record evidence-backed outcomes, evaluator findings, retries, regressions and DO/DON'T lessons. Promote patterns only after repeated evidence and evaluation.

Learning has two outputs:

`Outcome -> Advice Candidate`

and, when evidence supports a behavioral change:

`Outcome -> Executable Orchestration Candidate -> Static Validation -> Regression -> Safety -> Shadow -> Canary -> Promote -> Monitor -> Rollback`

The learning engine may generate executable orchestration candidates without waiting for human approval. Activation is automatic only after the required gates pass. This is the intended self-improvement loop.

Candidate selection should favor measurable improvement over a baseline, not merely novelty. Prefer candidates that improve acceptance or efficiency while preserving protected behavior, reducing regressions and maintaining verification quality. Maintain a portfolio of representative regression families so the optimizer does not overfit to the latest task.

Learned executable behavior may improve retrieval, routing, node selection, retry strategy, graph topology and orchestration decisions. It must not silently expand credentials, permissions or protected security boundaries.

Promoted orchestration remains versioned, content-addressed and reversible. Keep the parent digest, candidate digest, gate evidence, promotion decision and rollback lineage in the append-only journal.

## Recovery, rollback and safety

Failures are classified before recovery. Use targeted repair for actionable failures; do not restart the entire graph unless the failure invalidates its contract or required evidence.

Every promoted behavioral change must remain reversible. Rollback returns AER to the last known-good orchestration behavior without modifying the target repository. Security, permission and protected-behavior gates cannot be bypassed by learned strategies or retries.

For high-risk self-modifications, prefer shadow/canary exposure and automatic rollback based on predefined degradation thresholds rather than immediate full activation.

## Optional extensions

Extensions are capabilities, never dependencies. Detect first; use only when available, healthy, relevant and permitted; never install or modify them automatically.

Graphify/code-mem: structural and graph evidence. Superpowers: planning/TDD/debugging. Ponytail: minimal-change/regression checks. Caveman: compact context. LSP: optional diagnostics from an existing suitable server. Sandboxing: explicit future execution boundary; never silently enabled.

Precedence: `Repository/team rules > security/permissions > acceptance > local architecture > verification > orchestrator > extension > model preference`.

## Completion

Report: `Outcome | Changed files | Evidence | Verification | Regression checks | Review | Capability plan | Graph/loop summary | Learning signal | Self-modification candidate/promotion | Extensions | Assumptions | Risks | Incomplete checks | Efficiency`.

Policies: `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md`, `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`, `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `QUALITY_GOVERNANCE.md`.
