# Claude Code entry point

Use `AGENTS.md` for repository-wide engineering rules and `skills/ai-coding-orchestrator/SKILL.md` for the deployable adaptive coding skill.

For non-trivial software-engineering requests, invoke the adaptive orchestrator before editing. It classifies intent and risk, profiles the repository, discovers available optional skills/MCP integrations, retrieves targeted context, follows local naming and architecture conventions, implements, verifies, reviews, repairs when justified, and stops after one adaptive run unless the user explicitly requests a loop.

Optional extensions such as Graphify, code-mem/codebase-memory-mcp, Superpowers, Ponytail, Caveman, and other compatible skills are capabilities only. Never install, enable, grant permissions to, or modify them automatically.

When this skill is installed globally, the same contract applies to any repository in the active Claude Code context. Repository-local instructions always take precedence over global defaults.
