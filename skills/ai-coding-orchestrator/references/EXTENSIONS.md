# Optional Extensions

Extensions are capabilities, never core dependencies. Detect first; use only when installed, enabled, relevant, and permitted. Never install or modify them without explicit approval.

| Extension | Use for | Avoid |
|---|---|---|
| Graphify | AST, deterministic graph, relationships, impact/path evidence | duplicate queries when code-mem already provides the needed evidence |
| code-mem / codebase-memory-mcp | persistent code graph, semantic/structural search, call tracing, impact | replaying the same repository exploration |
| Superpowers | TDD, planning, systematic debugging, execution discipline | copying its full workflow when only one capability is needed |
| Ponytail | YAGNI and minimal-change pressure | removing required correctness, security, tests, or error handling |
| Caveman | compact output and subagent summaries | lossy compression of code, commands, errors, acceptance criteria, or verification evidence |
| Other Agent Skills/MCP | task-specific capability | speculative or redundant invocation |

Precedence is: repository/team rules > security/permissions > acceptance criteria > local architecture > verification > orchestrator > optional extensions > model preference.

When multiple providers return the same evidence, prefer the fresher, more authoritative, lower-cost result and retain provenance.
