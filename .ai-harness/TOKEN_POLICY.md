# Token and Tool Economy Policy

Context, model calls, tool calls, and command execution are all budgeted resources.

## Default strategy

Use the smallest context and least capable model that can safely solve the current phase.

Escalate budget when:

- uncertainty is unknown;
- risk is high or critical;
- verification fails;
- the task spans multiple architectural boundaries;
- independent review finds a material issue.

## Context priority

1. current task and acceptance criteria
2. repository instructions and architecture boundaries
3. relevant code and tests
4. relevant prior phase evidence
5. relevant learned patterns
6. general background

Drop low-value context before increasing the budget.

## Reuse

Cache or preserve stable repository context where the provider supports it. Reuse repository maps and phase summaries instead of regenerating equivalent content.

## Tool discipline

Load only tools required by the current phase. Avoid broad discovery after the relevant evidence is known.

## Completion economics

Do not reduce verification merely to save tokens. Optimize repeated context preparation and unnecessary exploration first.

Record token/tool metrics when the provider exposes them so future routing can learn which workflows are efficient and which are wasteful.
