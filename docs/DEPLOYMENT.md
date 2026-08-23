# AI Coding Orchestrator Deployment

The repository contains a deployable Agent Skill and an optional Claude Code plugin. The harness is provider-neutral and runs one adaptive orchestration per task by default.

## What gets installed

The portable skill lives at:

`skills/ai-coding-orchestrator/SKILL.md`

The Claude plugin manifest is:

`.claude-plugin/plugin.json`

The installer is:

`scripts/install_skill.py`

The installer is idempotent and backup-aware. It does not install third-party tools, change MCP configuration, change permissions, or overwrite user instructions without creating a `.ai-harness.bak` backup.

## Claude Code

Claude Code supports project/user memory and skills. A global installation can be performed with:

```bash
python scripts/install_skill.py --claude
```

or:

```bash
python scripts/install_skill.py --global
```

The installer places the skill under `~/.claude/skills/ai-coding-orchestrator/` and adds a small managed bootstrap block to `~/.claude/CLAUDE.md`. Restart Claude Code after installation.

For a project-scoped installation, install the plugin/skill through the normal Claude Code plugin/skill mechanism or copy the deployable skill into the repository's `.claude/skills/` location. Do not duplicate both global and project copies unless the project intentionally pins a version.

Claude Code also supports MCP servers. Optional code-intelligence tools such as Graphify and codebase-memory-mcp should be configured independently and only with explicit approval.

## Generic Agent Skills

For Agent-Skills-compatible clients:

```bash
python scripts/install_skill.py --agents
```

This installs under `~/.agents/skills/ai-coding-orchestrator/` without changing provider configuration.

## Gemini CLI

```bash
python scripts/install_skill.py --gemini
```

The skill is installed under `~/.gemini/skills/ai-coding-orchestrator/` and a managed bootstrap is added to `~/.gemini/GEMINI.md`.

## Optional extensions

The orchestrator discovers these when available:

| Extension | Role | Required |
|---|---|---|
| Graphify | AST/knowledge graph and relationship/impact evidence | No |
| code-mem / codebase-memory-mcp | Persistent code graph, semantic search, call/impact tracing | No |
| Superpowers | Process skills: brainstorming, TDD, debugging, planning, execution | No |
| Ponytail | YAGNI/minimal-change discipline | No |
| Caveman | Communication/subagent compression | No |
| Other Agent Skills | Task-specific capability | No |
| MCP servers | External tools/context | No |

Availability is detected with:

```bash
python .ai-harness/extension_registry.py
```

The detector is read-only. It never installs, updates, enables, disables, or rewrites an external tool.

## Extension conflict policy

Use this precedence:

1. Repository/team instructions
2. Security and permission boundaries
3. Acceptance criteria
4. Existing repository architecture and conventions
5. Verification requirements
6. AI Coding Orchestrator
7. Optional extension guidance
8. Model preference

Extensions complement one another rather than stack identical workflows. For example, Graphify/code-mem provide structural evidence, Superpowers provides a process technique, Ponytail reduces unnecessary implementation, and Caveman compresses communication. The orchestrator remains responsible for task routing, evidence selection, verification, and stopping.

## Any repository

The intended developer experience is:

```text
cd any-repository
claude

> Fix JIRA-1234 and add a regression test
```

The global skill and bootstrap make the orchestrator available without copying `.ai-harness/` into every repository. When a repository has its own `.ai-harness/`, that project configuration takes precedence over global defaults.

## Safety

The installer does not grant permissions, bypass prompts, or auto-enable dangerous tools. High-risk work remains subject to the coding agent's normal permission model and the repository's sandbox/worktree policy.

Optional third-party tools remain opt-in and externally owned. Review their current licenses, security posture, release integrity, and operational requirements before installation.
