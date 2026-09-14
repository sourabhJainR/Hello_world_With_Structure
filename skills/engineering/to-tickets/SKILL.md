---
name: to-tickets
description: Decompose a spec into small, independently verifiable tracer-bullet work units with explicit blocking relationships.
disable-model-invocation: true
---

# To Tickets

Turn a durable spec into the smallest useful work units. Tickets are implementation contracts, not a checklist of coding steps.

## Ticket rules

Each ticket must state:

- one outcome
- affected seam/module
- acceptance behavior
- verification evidence expected
- dependencies/blockers
- non-goals
- risk or compatibility notes

Prefer vertical slices that leave a working increment. Put blocking edges between tickets when one cannot be implemented or verified without another.

## Integration

Use the repository's existing issue/ticket mechanism. Do not introduce a second tracker. Tickets feed `implement`, which respects dependency order and the repository's mutation/verification gates.

Carry the original intent and context evidence digest into the ticket set so later implementation can trace decisions back to primary evidence.
