# Adaptive AI Coding Harness

A provider-neutral orchestration layer for Claude Code, Codex, Gemini CLI, local agents, and custom AI coding CLIs.

## Design

```text
Prompt / Task / Jira / Issue
          |
          v
   Adaptive Router
          |
   +------+-------+
   |      |       |
 intent  risk  uncertainty
   +------+-------+
          |
          v
 Relevant Memory + Repository Context
          |
          v
 Token Budget + Model Tier + Tool Policy
          |
          v
 Minimum Safe Capability Set
          |
          v
 Worktree Isolation when needed
          |
          v
 Understand -> Plan -> Execute
          |
          v
 Chunk -> Checkpoint -> Verify -> Continue
          |
          v
 Validate -> Independent Review -> Grill when needed
          |
          v
 Diff / Evidence Gate
          |
          v
 Learn -> Groom -> Reuse
```

## Execution discipline

The runtime is outcome-first and autonomous within configured safety boundaries.

For substantial tasks it breaks work into independently verifiable chunks and checkpoints after each meaningful phase. A checkpoint records the run/phase, state and output digests, changed files, scope decision and next action.

Every run continuously checks:

- **Scope:** changed files stay inside configured task roots; protected paths never change silently.
- **Context integrity:** detect loss of task focus or key constraints as context grows.
- **Guardrail integrity:** critical contract rules are re-established before risky continuation.
- **Unsupported claims:** model statements such as verified/proven/no-regression must have evidence before being treated as fact.
- **Progress:** repeated retries without new evidence trigger a strategy change instead of blind looping.

Routine low-risk work proceeds without repeated confirmation. Explicit confirmation remains reserved for destructive actions, production/external side effects, permission changes, and security-policy changes. This follows the current agent-harness direction of keeping ordinary work frictionless while making higher-risk actions explicit. citeturn843113search0turn843113search34

Long tasks use compact state and progressive context instead of transcript replay. Current agent guidance similarly favors structured state, incremental progress, and compaction over oversized persistent instructions. citeturn843113search1turn843113search4

## Automatic routing

Use the runner without selecting capabilities:

```bash
python .ai-harness/run.py run --task "Fix the intermittent export timeout"
python .ai-harness/run.py run --jira PROJ-1827 --task "Implement the requested change"
python .ai-harness/run.py run --jira-file ./jira/PROJ-1827.txt
```

The router chooses from:

```text
research  unknown facts, technologies, APIs, architecture options
debug     failures, regressions, intermittent behavior, root-cause analysis
poc       feasibility or major technical uncertainty
review    meaningful code changes
Grill     high-risk security, migration, performance, production or design decisions
```

Simple tasks stay simple. High-risk or uncertain tasks get stronger reasoning, stronger verification, isolation, or adversarial review.

## Legacy and data-shape safety

For legacy or poorly documented systems, the harness should discover before changing. It traces entry points, callers, branches, fallbacks, side effects, persistence and integrations; compares relevant data shapes; and keeps inferred or undocumented behavior separate from confirmed facts.

Use `runtime/legacy.py` for structural shape fingerprints, flow variants, evidence-linked paths, and bounded impact closure. Never store sample payload values as durable shape evidence.

## Engineering operating system

The harness applies:

```text
.ai-harness/principles.md
.ai-harness/ai-coding-best-practices.md
.ai-harness/agent-extensions.md
```

These encode language-neutral engineering practices including DRY, YAGNI, KISS, DI/dependency inversion, selective SOLID, cohesion/coupling, security by default, failure-aware design, observability, reversibility, behavior-focused testing, compatibility, least privilege, and evidence-based decision making.

The AI-specific policy adds context engineering, model/effort routing, bounded tools, controlled delegation, checkpointing, recovery, worktree isolation, independent review, verification gates, explicit stopping conditions, diff discipline, and governed self-improvement.

## Isolated worktrees

Use a separate Git worktree for risky or parallel mutating work:

```bash
python .ai-harness/worktree.py create feature-auth
python .ai-harness/worktree.py list
python .ai-harness/worktree.py remove feature-auth
```

Worktree policy is configured under `[worktrees]` in `config.toml`. High and critical risk work is eligible for automatic isolation when the orchestration layer is integrated with a worktree-capable provider.

Failed worktrees are kept by default so the failure can be inspected. Successful worktrees are not deleted automatically until their branch or changes are safely preserved.

## Independent review agents

Use independent, read-only review perspectives after meaningful changes:

```bash
python .ai-harness/review_agents.py \
  --agent claude \
  --run-dir .ai-harness/runs/<run> \
  --task "Review the implemented change" \
  --review correctness \
  --review security \
  --review architecture
```

Reviewer roles are intentionally independent of the implementing agent. They inspect the current repository and diff and produce evidence-backed findings without modifying files.

## Commands

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py capabilities
python .ai-harness/run.py context
python .ai-harness/run.py memory
python .ai-harness/run.py groom
python .ai-harness/run.py eval
python .ai-harness/run.py run --task "..."
python .ai-harness/run.py run --task "..." --dry-run
```

## Skills

Canonical AgentSkill:

```text
.agents/skills/ai-coding-orchestrator/SKILL.md
```

Claude-specific entry point:

```text
.claude/skills/ai-coding-orchestrator/SKILL.md
```

The repository-wide instruction surface is `AGENTS.md`.

## Run state and context

Each run captures route state, repository context, prompts, phase outputs, validation evidence, execution-control checkpoints, and final git state under:

```text
.ai-harness/runs/<timestamp>/
```

Long-running work should preserve compact checkpoints rather than replaying the full transcript.

## Learning and evaluation

Memory is split into observations and patterns:

```text
.ai-harness/memory/
  observations.jsonl
  patterns.jsonl
```

Representative routing tasks live under `.ai-harness/evals/cases.jsonl`. Changes to routing, prompts, principles, model policy, or review policy should be compared against representative tasks before promotion.

A run can add observations and candidate lessons. Grooming merges repeated lessons and promotes patterns only after configurable evidence and success-rate thresholds. Model output never edits harness code, provider permissions, or permanent rules directly.

## Model and tool routing

The harness supports provider-neutral model/effort tiers. The policy is to use the least capable model and reasoning effort that safely solves the current phase, escalating when uncertainty, risk, failed verification, or task horizon increases.

Tool access follows the same rule: expose only the tools relevant to the current phase, prefer read-only investigation before mutation, and use isolated worktrees or sandboxes for risky or parallel work.

## Jira

The harness accepts `--jira` and `--jira-file`. For a Jira key, the selected AI CLI is instructed to retrieve the issue through an available Jira or MCP integration when one exists. A local Jira export can always be supplied with `--jira-file`.

## Token optimization

The router has separate budgets for routing, memory, context and phase history. Repository context is built as a compact file/symbol map, and only relevant memory is included. Stable instructions and reusable repository context should remain cache-friendly for providers that support prompt caching or compaction.

The system follows the current agent guidance to keep prompts lean, expose only relevant tools, track context as it grows, and use structured checkpoints/compaction for long tasks. citeturn843113search2turn843113search7

## Safety and self-improvement boundaries

Research and Grill phases are read-only by contract. POCs are experimental. Production changes happen only during execution phases. Retries require new evidence or a changed approach.

The harness can improve its learned knowledge and routing candidates, but it does not silently rewrite its own executable code, security policy, provider permissions, or permanent engineering rules. System changes require normal review and validation.
