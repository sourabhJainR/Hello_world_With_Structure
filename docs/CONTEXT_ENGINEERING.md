# Context engineering, memory and task handoffs

AER treats context as a bounded resource, not a transcript to forward between agents.

## Memory ownership

There are three deliberately separate layers:

1. **Private working memory** — owned by the executing agent. It is optional, run-scoped, bounded and disposable. It helps the agent remember local discoveries without distracting it with team bookkeeping.
2. **Shared task memory** — owned by the orchestration run. It contains only bounded handoffs needed by downstream agents. Old entries are evicted when budgets are reached.
3. **Durable learning ledger** — owned by the learning steward. It records reusable, evidence-backed lessons for current and future runs. Execution agents cannot promote their private notes directly into this store.

Repository files, tests and other authoritative evidence remain the source of truth. Memory is a cache of useful knowledge, not a replacement for verification.

## Guardrails

- Every memory layer has hard size/count limits.
- Private memory is isolated by agent and run ID.
- Shared task memory is isolated by task intent digest.
- Concurrent writes use process-safe file locks and atomic replacement.
- Durable learning uses SQLite WAL transactions with a busy timeout for concurrent agents/processes.
- Durable records are append-only observations. A record carries `schema_version`, `learning_version`, revision, run, source agent and evidence references.
- Duplicate observations are idempotent through a content fingerprint.
- Learning defaults to `candidate`; it is not treated as verified merely because an agent said it worked.
- Rejected/superseded learning is not silently presented as current guidance.
- Long logs, complete transcripts, speculative reasoning and repeated tool output are never copied into durable learning.
- When context becomes too large, low-value/old working entries are evicted instead of failing the task.
- A single oversized memory item is rejected rather than breaking the memory budget.
- No memory operation requires a specific model provider or a second LLM summarizer.

## Learning steward

The execution agent should spend its effort on the task. The `learning-steward` is a separate, non-critical role that receives the completed team evidence and performs the peripheral learning work.

The steward records explicit outcomes such as `worked`, `failed`, `partial` and `regressed`, together with the approach and evidence. Historical learning is injected into later runs as guidance, but agents are instructed to verify important claims against the current repository.

The durable ledger is intentionally detailed but bounded. The current schema is version `2`, learning format `2.0`; future schema changes should migrate data rather than silently reinterpret old records.

## Handoff contract

A handoff contains only:

- objective
- completed status
- decisions
- evidence
- unresolved risks
- relevant files
- next action

The receiver gets direct dependency handoffs plus planner context rather than the complete run transcript.

## Model neutrality

The orchestration layer does not depend on a model-specific context format, tokenizer, prompt syntax or summarizer. A stronger model can improve the quality of the agent result without changing the orchestration contract. A weaker or local model receives the same bounded structured context.
