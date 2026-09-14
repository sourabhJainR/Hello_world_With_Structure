---
name: domain-modeling
description: Keep domain terms precise, resolve overloaded concepts, and record durable vocabulary decisions.
---

# Domain Modeling

Treat language as part of the design. Before changing a concept, find how the repository currently names it in code, tests, context documents, and ADRs.

## Discipline

- Use one term for one concept where practical.
- When a term has multiple responsibilities, split the concepts rather than hiding the ambiguity in one type.
- When a new durable concept is introduced, update the repository glossary/context at the same change boundary.
- Record hard-to-reverse naming or ownership decisions as ADRs when they will guide future work.

## Integration

Domain language feeds `ContextEvidence`, skill routing, test names, and architecture reviews. Do not create a separate domain-memory store. The repository's context and ADR mechanisms remain authoritative.

When domain wording is uncertain, pause implementation long enough to resolve the term. A precise name is part of the seam: it reduces context needed by both humans and agents.
