# Optional Extensions

Extensions are capabilities, never core dependencies. Detect first; use only when installed, enabled, relevant, and permitted. Never install or modify them without explicit approval.

| Extension | Use for | Avoid |
|---|---|---|
| Graphify | AST, deterministic graph, relationships, impact/path evidence | duplicate queries when code-mem already provides the needed evidence |
| code-mem / codebase-memory-mcp | persistent code graph, semantic/structural search, call tracing, impact analysis | replaying the same repository exploration |
| Superpowers | TDD, planning, systematic debugging, execution discipline | copying its full workflow when only one capability is needed |
| Ponytail | YAGNI, minimal-change pressure, and explicit regression/behavior-preservation thinking | treating a small diff as proof of safety; removing required correctness, security, tests, or error handling |
| Caveman | compact output and subagent summaries | lossy compression of code, commands, errors, acceptance criteria, or verification evidence |
| Other Agent Skills/MCP | task-specific capability | speculative or redundant invocation |

## Ponytail-inspired change discipline

When Ponytail is available, use it as a constraint on scope rather than as an authority over repository correctness:

1. State the exact behavior that must change.
2. Identify behavior that must not change.
3. Inspect affected callers, consumers, contracts, shared state, error paths, and sibling flows.
4. Make the smallest safe change that satisfies the contract.
5. Avoid unrelated refactoring, cleanup, renaming, formatting, dependency changes, and speculative abstractions.
6. Prove the intended behavior and regression-check relevant unaffected flows.
7. If a broader change is required, explain why the narrower change would be unsafe or incomplete.

When multiple providers return the same evidence, prefer the fresher, more authoritative, lower-cost result and retain provenance.

Precedence is: repository/team rules > security/permissions > acceptance criteria > local architecture > verification > orchestrator > optional extensions > model preference.
