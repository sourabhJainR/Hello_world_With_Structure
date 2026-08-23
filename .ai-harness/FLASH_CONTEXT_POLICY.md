# Flash-Context Policy

This harness uses a FlashAttention-inspired context-engineering principle. It does not implement or install FlashAttention itself.

FlashAttention is IO-aware: it reduces expensive memory movement by working on useful tiles and reusing data instead of materializing the full attention matrix. The coding-agent equivalent is to reduce prompt IO by keeping stable context compact and selecting only the most relevant evidence for each phase.

## Principles

1. Stable prefix: repository instructions, project profile, engineering principles, and task contract should remain small and stable.
2. Tiled context: split repository evidence into structural, semantic, task-local, and validation tiles.
3. Reuse before reread: do not resend unchanged evidence merely because a new phase started.
4. Sparse retrieval: rank files, memory, and prior outputs by task relevance rather than sending the repository wholesale.
5. Budget first: every context source has a character/token budget.
6. Fuse summaries: combine related evidence into compact summaries before adding it to a provider prompt.
7. Recent evidence wins: current command output and current diff outrank stale memory.
8. Negative evidence matters: failed approaches and rejected findings can prevent repeated work.
9. Preserve provenance: every selected context block should retain its source or artifact identity.
10. Verification is never compressed away: acceptance evidence, failures, security findings, and required test output remain intact.

## Context tiers

- L0: task, constraints, acceptance criteria, stopping condition
- L1: repository instructions and local conventions
- L2: compact repository structure and relevant symbols
- L3: task-relevant files and interfaces
- L4: current diff, validation output, review findings
- L5: learned memory and historical evidence

Lower-numbered tiers are more stable and should be reused. Higher-numbered tiers are more selective and phase-specific.

## Anti-patterns

Do not:

- resend full prior transcripts;
- dump the entire repository into every prompt;
- let stale memory outrank current repository evidence;
- reduce verification evidence merely to meet a token budget;
- add a vector database or third-party retrieval stack when local deterministic ranking is sufficient.

The optimizer is deterministic, local, language-neutral, and dependency-free by default.
