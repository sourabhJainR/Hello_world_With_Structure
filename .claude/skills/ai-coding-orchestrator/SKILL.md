---
name: ai-coding-orchestrator
description: Adaptive repository-aware control plane for software engineering. Challenges requirements, selects the minimum safe workflow, uses bounded evidence, preserves local conventions, makes minimal changes, verifies regressions, and produces proof-backed outcomes.
---

Use this skill as the Claude Code entrypoint for the provider-neutral Adaptive AI Coding Orchestrator. Keep this entrypoint small; load detailed policy only when needed.

Lifecycle: `Understand -> Profile -> Specify -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if justified -> Learn -> Stop`

Do not self-loop unless the user explicitly requests a bounded loop.

Core rules:

- Challenge consequential ambiguity instead of agreeing blindly. For meaningful work establish goal, non-goals, requirements, constraints, protected behavior, boundaries, acceptance, risks, and assumptions.
- Read repository/team/platform instructions and inspect existing structure, tests, architecture, exception handling, logging, telemetry, DI, configuration, dependencies, and placement before editing.
- Make the minimum safe change. Preserve behavior outside the contract and regression-check relevant callers, sibling paths, negative/error paths, compatibility, state transitions, and integrations.
- Treat architecture as phase- and context-dependent. Check boundaries, separation of concerns, data-model integrity, failure handling, operational discipline, and observability.
- For research/flow work, use `Fact | Inference | Unknown | Recommendation` and trace actual evidence; do not present guesses as facts.
- Use Graphify, code-mem, Superpowers, Ponytail, Caveman, MCP, and other skills only when available, permitted, relevant, and useful.
- Keep context bounded and deduplicated. Optimize verified outcome per token, call, retry, and latency.
- Maintain the Engineering State Ledger for meaningful work and stop non-progressing retries.

Progressive policies: `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md` (opt-in only), `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`, `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `QUALITY_GOVERNANCE.md`, plus `skills/ai-coding-orchestrator/references/` and `docs/`.

Do not install or modify optional extensions without explicit approval. Do not claim success without verification evidence.