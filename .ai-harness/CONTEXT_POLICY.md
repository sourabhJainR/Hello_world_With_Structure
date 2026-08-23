# Context Engineering Policy

Use progressive disclosure.

1. Start with repository instructions and task contract.
2. Load the project convention profile.
3. Load the smallest relevant architecture and domain map.
4. Retrieve only task-relevant memory.
5. Add targeted files, symbols, tests, logs, and command output.
6. Compress prior phase output into decisions, evidence, failures, and open questions.

Do not replay entire transcripts or repository dumps unless required for recovery.

Stable context should remain reusable and cache-friendly where the provider supports prompt caching or compaction.

Repository knowledge should be versioned and local whenever practical. High-value knowledge includes architecture boundaries, quality rules, security rules, reliability constraints, plans, decision records, and verification commands.

A context item should have a reason for inclusion. When context exceeds budget, remove low-relevance material before increasing the budget.
