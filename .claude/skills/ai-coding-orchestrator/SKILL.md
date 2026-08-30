---
name: ai-coding-orchestrator
description: Adaptive repository-aware control plane for software engineering. Challenges ambiguous requirements, selects the smallest safe workflow, retrieves bounded evidence, preserves local architecture, makes minimal changes, verifies regressions, and produces evidence-backed outcomes.
---

Use this skill as the provider-neutral control plane for non-trivial software engineering work. The canonical operating contract is at `skills/ai-coding-orchestrator/SKILL.md`; detailed policy is loaded progressively only when needed.

Default lifecycle:

`Understand -> Profile -> Specify -> Retrieve -> Route -> Execute -> Verify -> Review -> Repair if justified -> Learn -> Stop`

Normal runtime is one adaptive run. Never self-loop unless the user explicitly requests a bounded loop.

Core behavior:

- Challenge consequential ambiguity before implementation; separate requirements, non-goals, protected behavior, boundaries, acceptance criteria, risks, and assumptions.
- Preserve repository-native naming, placement, architecture, exception handling, logging, telemetry, DI, configuration, dependencies, and testing patterns.
- Make the smallest safe change and explicitly check relevant unaffected flows for regressions.
- Treat architecture as phase- and context-dependent; avoid both premature complexity and unsafe prototype shortcuts.
- For research/flow requests, use evidence-first reporting with facts, inferences, unknowns, provenance, and detailed traceability.
- Use Graphify, code-mem, Superpowers, Ponytail, Caveman, MCP, and other skills only when available, permitted, relevant, and materially useful.
- Keep context bounded and deduplicated; optimize verified outcome per token/call/latency rather than raw token count.
- Maintain compact Engineering State and proof/evidence chains for non-trivial work; detect and stop thrashing.

Load the canonical skill and detailed references when the task requires deeper guidance. Do not copy references into every prompt.