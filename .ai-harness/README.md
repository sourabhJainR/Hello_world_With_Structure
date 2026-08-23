# Adaptive AI Coding Harness

A provider-neutral orchestration layer for Claude Code, Codex, Gemini CLI, local agents, and custom AI coding CLIs.

The design borrows useful patterns from mature coding-agent projects: always-loaded repository instructions and triggerable skills from OpenHands, focused token-bounded repository maps from Aider, and reproducible run evidence from SWE-agent.

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
 Minimum Safe Capability Set
          |
          v
 Execute -> Validate -> Review / Grill
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

Simple tasks stay simple. High-risk or uncertain tasks get more reasoning.

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

## State and context

Each run creates:

```text
.ai-harness/runs/<timestamp>/
  manifest.json
  task.txt
  repository-map.md
  route.prompt.md
  route.output.md
  <phase>.prompt.md
  <phase>.output.md
  validation.log
```

Only compact phase evidence is passed forward. The runner also keeps a relevance-ranked memory store.

## Learning

Memory is split into observations and patterns:

```text
.ai-harness/memory/
  observations.jsonl
  patterns.jsonl
```

A run can add observations and candidate lessons. Grooming merges repeated lessons and promotes a pattern only after configurable evidence and success-rate thresholds. Model output never edits harness code or permanent rules directly.

## Jira

The harness accepts `--jira` and `--jira-file`. For a Jira key, the selected AI CLI is instructed to retrieve the issue through an available Jira or MCP integration when one exists. A local Jira export can always be supplied with `--jira-file`.

## Token optimization

The router has separate budgets for routing, memory, context and phase history. Repository context is built as a compact file/symbol map, and only relevant memory is included. This follows the same general token-budget principle as Aider's repository map.

## Safety

Research and Grill phases are read-only by contract. POCs are experimental. Production changes happen only during execution phases. The harness never self-edits its own Python implementation from learned model output.
