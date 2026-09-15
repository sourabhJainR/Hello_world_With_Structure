# Context engineering and task handoffs

AER treats context as a bounded resource, not a transcript to forward between agents.

## Rules

1. The task contract is always present.
2. An agent receives only its direct dependency handoffs plus the planner handoff.
3. Context is deduplicated, ranked and bounded before it reaches the model.
4. Verified evidence and decisions outrank raw model output.
5. Agent output is converted into one bounded handoff. Raw output is never used as an unlimited shared transcript.
6. Durable project memory is separate from task working memory and must not become a dump of conversations.
7. When a path repeatedly produces low-value or oversized context, it is compacted or dropped rather than forwarded.
8. No context-management step requires a particular model provider or a second summarization model.

## Handoff contract

A handoff contains only:

- objective
- completed status
- decisions
- evidence
- unresolved risks
- relevant files
- next action

The receiver is responsible for validating important inherited claims against current repository evidence.

## Memory policy

Task working memory is temporary and bounded. Durable memory should contain stable, reusable information such as verified project decisions, repository conventions, or explicit user-approved facts. Large logs, repeated tool output and speculative reasoning do not belong in durable memory.

The existing `PersistentMemory` remains the durable memory owner. `SharedTaskMemory` remains the per-run working-memory owner. `ContextEngine` is the single packing/ranking boundary between them and model prompts.

## Model neutrality

The orchestration layer does not depend on a model-specific context format, tokenizer, prompt syntax, or summarizer. A stronger model can improve the quality of the agent result; AER keeps the surrounding execution contract stable. A weaker or local model still receives the same small, structured context.

This separation lets model and agent capabilities improve independently of orchestration mechanics.
