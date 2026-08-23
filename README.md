# Adaptive AI Coding Orchestrator

Provider-neutral AI software engineering orchestration designed to sit above Claude Code, Codex, Gemini CLI, local agents, and other compatible coding-agent environments.

The repository is distributed as a deployable Agent Skill and Claude Code plugin. Its intended product identity is `adaptive-ai-coding-orchestrator`; the GitHub repository name is retained temporarily for history compatibility.

## What it provides

```text
User task / Jira / issue
  -> repository rules + state
  -> extension discovery
  -> AST / graph / exact / semantic evidence
  -> FlashAttention-inspired bounded context
  -> adaptive workflow selection
  -> implementation / research / POC / debug / grill / review
  -> repository-native verification
  -> independent review and repair
  -> evidence-backed learning
```

Core principles:

- Repository conventions before generic conventions.
- Verification over model claims.
- Least privilege and isolated execution for risky work.
- Optional integrations, never mandatory dependencies.
- One adaptive runtime run by default; loops require explicit user intent.
- Stable context plus targeted evidence instead of full-repository prompting.
- Language and framework neutrality.

## Install for Claude Code

From Claude Code:

```text
/plugin marketplace add sourabhJainR/Hello_world_With_Structure
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

For local plugin development:

```text
/plugin marketplace add .
/plugin install adaptive-ai-coding-orchestrator@adaptive-ai-engineering
```

## Install on a developer box

```bash
./install.sh
```

or:

```bash
python3 scripts/install_skill.py --auto
```

The installer detects supported agent environments and installs the skill with backups. It does not install third-party tools, modify MCP configuration, grant permissions, or silently change external integrations.

## Optional intelligence extensions

The orchestrator can use these when already installed and enabled:

- Graphify for deterministic AST and relationship graphs.
- code-mem / codebase-memory-mcp for persistent codebase memory, structural search, semantic retrieval, call tracing and impact analysis.
- Superpowers for planning, TDD, systematic debugging and execution discipline.
- Ponytail for YAGNI and minimal-change discipline.
- Caveman for compact context/output handling.
- Other compatible Agent Skills and MCP servers discovered at runtime.

No extension is required for core operation.

## Architecture

See `docs/PLUGIN_ARCHITECTURE.md` and `docs/MARKETPLACE.md` for packaging, extension contracts, installation and release guidance.

## Safety

The orchestrator never silently installs tools, modifies permissions, connects to production, merges changes, or promotes learned behavior into executable policy. Repository and organization instructions remain authoritative.

## Development

Run the repository tests:

```bash
python -m unittest discover -s tests -v
```

Validate the distributable package:

```bash
python scripts/validate_plugin.py
```
