# Context Budget Policy

Context is a finite engineering resource. The orchestrator must optimize for useful evidence, not maximum retrieval.

## Retrieval funnel

```text
repository
  -> task scope
  -> symbols / graph paths
  -> exact and semantic search
  -> ranked evidence
  -> compact context
  -> model
```

## Default budget

Every workflow should track at least:

- estimated input tokens;
- estimated output tokens;
- tool calls;
- retrieved files/chunks;
- duplicate evidence ratio;
- cache reuse;
- latency.

If an implementation can answer a question with signatures and a small dependency slice, do not retrieve full files.

## Context classes

### Always loaded

Only stable, high-value instructions:

- task contract;
- applicable safety rules;
- repository authority;
- current workflow state;
- output contract.

### On demand

- detailed workflow instructions;
- provider documentation;
- architecture references;
- historical evidence;
- extension-specific guidance.

### Never automatically loaded

- entire repository;
- entire Git history;
- all tool schemas;
- previous transcripts unrelated to the current task;
- large generated artifacts.

## Compression rules

1. Deduplicate identical or overlapping evidence.
2. Prefer symbol-level summaries over full source when sufficient.
3. Prefer graph paths over unrelated neighboring code.
4. Preserve source provenance for every important claim.
5. Preserve uncertainty instead of compressing it away.
6. Stop retrieval when additional evidence has low expected value.

## Adaptive expansion

Start small. Expand only when:

- evidence conflicts;
- a dependency boundary is crossed;
- tests fail;
- confidence is below the task threshold;
- the user explicitly requests deeper investigation.

## Anti-bloat guardrails

A workflow must not load an optional skill merely because it exists. Skill selection must be capability- and task-driven.

A provider must not bypass the context budget. Large provider results must be summarized or ranked before model injection.
