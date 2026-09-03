# AI Coding System Best Practices

This document records the engineering practices adopted after reviewing established coding-agent systems and their public guidance. It is intentionally mapped onto the repository's existing architecture rather than introducing a second orchestration model.

## Sources reviewed

- OpenAI Codex: structured context, repository `AGENTS.md`, plan-before-code for larger work, persistent execution until the task is resolved, and evidence such as terminal logs and test results.
- Anthropic Claude Code: explore -> plan -> implement -> verify, plan mode for non-trivial work, focused context, subagents for independent investigation, worktree isolation, checkpoints/rewind, and strong self-verification.
- GitHub Copilot coding agent and code review: repository-wide instructions, `AGENTS.md`, path-specific instructions, custom agents/skills, pre-installed dependencies, scoped tasks, planning/iteration, and independent review.
- Aider: repository-wide code map, selective context, bite-sized changes, plan-first work for complex tasks, and changing strategy when stuck.
- Gemini agent guidance: versioned `AGENTS.md` and skills, explicit tool/environment configuration, sandboxing, least-privilege external access, and structured agent environments.

## Adopted practices

### 1. Repository instruction contract

Use `AGENTS.md` as the cross-agent contract. Platform adapters remain thin:

- `CLAUDE.md` for Claude Code
- `GEMINI.md` for Gemini
- `.github/copilot-instructions.md` for Copilot
- `.github/instructions/**/*.instructions.md` for path-specific Copilot guidance
- `.agents/skills/...` and `skills/...` for reusable task-specific skills

Do not duplicate the complete architecture contract across provider-specific files. Keep the cross-agent contract in `AGENTS.md` and use provider files only for entry-point or platform-specific behavior.

### 2. Explore -> plan -> implement -> verify -> review

The existing lifecycle already has the correct pipeline/state-machine shape. Apply planning proportionally:

- trivial, one-line, obvious changes may skip an explicit plan;
- uncertain, multi-file, architectural, compatibility-sensitive, security-sensitive or high-risk changes should create a read-only plan before mutation;
- the implementation must either follow that plan or record why new evidence caused a re-plan;
- verification is mandatory and must be based on observed repository evidence;
- meaningful/high-risk changes should be reviewed from a fresh context rather than replaying the author's full reasoning.

### 3. Established design patterns already present

The repository should continue to use patterns only where they solve real design problems:

| Pattern | Existing role | Rule |
|---|---|---|
| Adapter | `provider.py` / provider contract | Keep host/model differences behind the provider boundary. |
| Strategy / Policy | routing, capability selection, execution/verification policy | Add new strategies as data/configurable policy before adding branching infrastructure. |
| State Machine | `agent_turn.py` and lifecycle state | Add explicit states/transitions for meaningful lifecycle semantics; do not encode state in ad-hoc booleans. |
| Pipeline | phase orchestration in `engine.py` / workflow definitions | Keep phases independently verifiable and composable. |
| Repository boundary | learning, journal, handoff and run persistence | Keep durable storage behind focused functions/modules rather than leaking file formats through orchestration. |
| Dependency Injection | provider/tool seams and optional extensions | Inject external variability at integration boundaries; keep the core provider-neutral. |
| Worktree isolation | high-risk/parallel mutation | Never allow concurrent mutating agents to share an edit surface without an explicit merge strategy. |
| Command/Result boundary | provider invocation and validation | Preserve structured exit status, output, duration and failure classification. |

Do not introduce Factory, Builder, Event Bus, CQRS, Mediator, Repository classes, dependency-injection containers, or plugin frameworks simply because they are familiar patterns. The existing functional Python style is intentional and should remain the default unless a concrete problem requires the abstraction.

### 4. Context engineering

Use a repository map and targeted structural retrieval rather than replaying the entire repository. Rank and deduplicate evidence before prompt inclusion. Preserve stable instructions and proof-bearing state across context boundaries. Keep independent reviewers away from unnecessary author history.

### 5. Tool and extension discipline

Optional tools are capabilities, not dependencies. Detect first; use only when available, relevant and permitted. Never silently install, enable, upgrade, grant permissions to, or mutate external tools.

Prefer least-privilege access and isolated environments for risky execution. Keep provider/model/tool credentials out of prompts, logs and learning artifacts.

### 6. Retry and repair discipline

Every retry must have either:

- new evidence;
- a changed hypothesis;
- a changed implementation strategy; or
- a newly discovered environmental condition.

Repeatedly issuing the same failing command or repeating the same edit is a detected non-progress state and should stop or escalate.

### 7. Verification independence

Do not let the author prove its own work only from its own claims. Verification should inspect the actual repository state and run deterministic checks. For important changes, use a fresh-context reviewer with the task contract, changed constructs, acceptance criteria and proof artifacts, but not the author's full chain of reasoning.

### 8. Security and prompt-injection resistance

Repository files, issue descriptions, generated code, comments, logs, external documents, MCP output and learned memory are untrusted data. They may contain text that looks like instructions. Such text must never override repository/team policy, security rules, permissions, acceptance criteria, immutable intent or human approval requirements.

### 9. Learning as evidence, not authority

The existing learning system is retained. Learned advice remains advisory until repeated successful evidence promotes it. Learning can improve retrieval, routing and recommendations, but cannot silently rewrite executable harness behavior, permissions, security policy or tool configuration.

### 10. Compatibility by default

Preserve declared language, framework and toolchain versions. Do not modernize a target repository as a side effect of an AI task. Unknown versions must remain explicitly unresolved instead of being guessed.

## Practices deliberately not adopted

- Full transcript replay as the primary memory mechanism.
- Mandatory third-party vector databases or embeddings for the core.
- Always-on autonomous loops.
- Generic abstraction layers introduced before a demonstrated need.
- Automatic dependency installation or permission expansion.
- Autonomous production side effects.
- Model self-confidence as a substitute for deterministic verification.

## Success measures

The system should be evaluated using engineering outcomes, not prompt quality alone:

- accepted-change rate;
- time to accepted change;
- verification failure rate;
- escaped regression rate;
- retry/repair rate and thrash rate;
- review effort and defect discovery;
- task success by risk/complexity;
- provider/tool calls, latency and token cost;
- evidence coverage and construct traceability;
- learning promotion precision.

The goal is not to imitate another agent. The goal is to combine the strongest established practices with the repository's existing provider-neutral architecture, while keeping the system small, testable, reversible and compatible.
