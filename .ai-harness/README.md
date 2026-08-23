# Adaptive AI Coding Harness

A provider-neutral orchestration layer for Claude Code, Codex, Gemini CLI, local agents, and custom AI coding CLIs.

The design borrows useful patterns from mature coding-agent projects: always-loaded repository instructions and triggerable skills, focused token-bounded repository maps, reusable skills, controlled delegation, and reproducible run evidence.

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
 Token Budget / Context Planner
          |
          v
 Model + Tool + Capability Routing
          |
          v
 Understand -> Plan -> Execute
          |
          v
 Verify -> Diff Review -> Grill when needed
          |
          v
 Learn -> Groom -> Reuse
```

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
poc       feasibility or major technical uncertainty
debug     failures, regressions, intermittent behavior, root-cause analysis
review    meaningful code changes
Grill     high-risk security, migration, performance, production or design decisions
```

Simple tasks stay simple. High-risk or uncertain tasks get more reasoning, stronger verification, or adversarial review.

## Engineering operating system

The harness applies two complementary policy layers:

```text
.ai-harness/principles.md
.ai-harness/ai-coding-best-practices.md
```

They encode language-neutral practices including DRY, YAGNI, KISS, DI/dependency inversion, selective SOLID, cohesion/coupling, security by default, failure-aware design, observability, reversibility, behavior-focused testing, compatibility, least privilege, and evidence-based decision making.

The AI-specific playbook adds context engineering, model/effort routing, bounded tools, controlled multi-agent delegation, checkpoints, recovery, verification gates, diff discipline, explicit stopping conditions, and governed self-improvement.

## Commands

```bash
python .ai-harness/run.py providers
python .ai-harness/run.py capabilities
python .ai-harness/run.py context
python .ai-harness/run.py memory
python .ai-harness/run.py groom
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

## State, checkpoints and context

Each run creates a resumable evidence directory:

```text
.ai-harness/runs/<timestamp>/
  manifest.json
  task.txt
  repository-map.md
  route.prompt.md
  route.output.md
  checkpoint.json
  <phase>.prompt.md
  <phase>.output.md
  validation.log
```

Only compact phase evidence is passed forward. The runner keeps a relevance-ranked memory store rather than replaying full transcripts.

## Learning and evaluation

Memory is split into observations and patterns:

```text
.ai-harness/memory/
  observations.jsonl
  patterns.jsonl
```

Representative routing cases live under `.ai-harness/evals/cases.jsonl`. Changes to routing, prompts, or model policy should be evaluated against representative tasks before promotion.

A run can add observations and candidate lessons. Grooming merges repeated lessons and promotes patterns only after configurable evidence and success-rate thresholds. Model output never edits harness code, provider permissions, or permanent rules directly.

## Model and tool routing

The harness supports model/effort tiers through provider-neutral configuration. The intended policy is to use the least capable model and reasoning effort that safely solves the current phase, escalating when uncertainty, risk, failed verification, or task horizon increases.

Tool access follows the same rule: expose only the tools relevant to the current phase, prefer read-only investigation before mutation, and use isolated worktrees or sandboxes for risky or parallel work where supported.

## Jira

The harness accepts `--jira` and `--jira-file`. For a Jira key, the selected AI CLI is instructed to retrieve the issue through an available Jira or MCP integration when one exists. A local Jira export can always be supplied with `--jira-file`.

## Token optimization

The router has separate budgets for routing, memory, context and phase history. Repository context is built as a compact file/symbol map, and only relevant memory is included. Stable instructions and reusable repository context should remain cache-friendly for providers that support prompt caching or compaction.

## Safety and self-improvement boundaries

Research and Grill phases are read-only by contract. POCs are experimental. Production changes happen only during execution phases. Retries require new evidence or a changed approach. Long-running work uses checkpoints for recovery.

The harness can improve its learned knowledge and routing candidates, but it does not silently rewrite its own executable code, security policy, provider permissions, or permanent engineering rules. System changes require normal review and validation.
