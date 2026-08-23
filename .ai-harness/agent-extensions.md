# AI Agent Extensions

The harness is designed as an operating layer around any coding agent or CLI.

## Context engineering

Maintain a small stable prefix:

1. repository instructions
2. principles and task contract
3. compact repository map
4. relevant memory
5. current task

Then add only phase-specific evidence. Prefer summaries, targeted files, and fresh command results over full transcripts.

When a provider supports prompt caching or compaction, keep stable instructions and repository context cacheable and let transient task evidence remain dynamic. Current OpenAI model guidance recommends lean prompts, explicit success criteria, relevant tools only, and context tracking as the run grows. citeturn817632search0turn817632search2

## Model routing

Select the least capable model that meets the task risk and complexity. Escalate for:

- high uncertainty
- difficult debugging
- architecture decisions
- security-sensitive work
- cross-repository changes
- long-horizon implementation
- failed verification loops

Prefer low-cost routing and summarization models for classification and compression, and stronger coding models for implementation and hard review. Reasoning effort should be selected deliberately rather than always maxed. OpenAI's current guidance explicitly recommends tuning reasoning effort and testing a lower setting when quality is preserved. citeturn817632search0turn817632search2

## Tool governance

Expose only the tools needed for the current phase. Separate read-only investigation from mutation where the provider supports permissions or isolated agents. Use least privilege for credentials and external access.

## Multi-agent delegation

Delegate only independent work that can be safely parallelized. Good candidates:

- independent codebase investigations
- alternative design research
- independent review perspectives
- test planning
- security review

Do not parallelize edits to the same files or tightly coupled design decisions without an explicit merge strategy. Current agent guidance increasingly favors controlled subagent delegation for tasks that divide cleanly. citeturn817632search0

## Verification loop

Never stop at generation. Use:

```text
Understand -> Plan -> Change -> Verify -> Inspect diff -> Review -> Learn
```

On failure:

```text
Failure -> Diagnose -> Minimal fix -> Re-verify
```

Cap retry loops and require new evidence between attempts. Do not repeat the same failed action unchanged.

## Checkpointing

For long-running tasks, record:

- current objective
- completed work
- files changed
- tests/checks passed
- failures and hypotheses
- next action
- unresolved decisions

A new model/session must be able to resume from the checkpoint without replaying the complete transcript.

## Recovery

A run should be resumable after provider failure, timeout, context compaction, or operator interruption. Persist route, phase, artifacts, validation status, and checkpoint state.

## Diff and completion gates

A completion gate should verify, when applicable:

- acceptance criteria
- relevant tests
- build/type/lint checks
- migration safety
- public contract impact
- security concerns
- performance concerns
- final diff cleanliness

## Learning and evaluation

Treat each completed task as an evaluation sample. Record:

- route chosen
- capabilities used
- model/provider
- token estimates when available
- retries
- validation result
- review findings
- useful lessons

Use representative regression tasks to compare router/prompt changes before promoting them. Never treat raw model confidence as proof of correctness.

## Self-improvement boundaries

The system may learn and groom routing knowledge, patterns, and task memories. It must not silently rewrite its executable runner, security policy, provider permissions, or permanent engineering rules. Code or policy changes require normal review and validation.
