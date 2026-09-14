---
name: improve-codebase-architecture
description: Survey recently changed or high-friction areas for deepening opportunities; propose candidates without mutating the repository.
disable-model-invocation: true
---

# Improve Codebase Architecture

This is a read-only survey. It finds places where the codebase is becoming harder to understand, test, or change. It does not silently refactor production code.

## Scope

Start with recent commit hotspots or a user-named subsystem. Use repository structure, symbols, dependency/graph evidence, tests, and current contracts. Prefer areas with repeated edits or weak seams over broad stylistic cleanup.

## Candidate test

For each candidate ask:

- Is the module shallow relative to its interface?
- Does understanding one behavior require unnecessary hops across modules?
- Are callers coupled to internal data or lifecycle mechanics?
- Is there a missing behavioral seam that makes verification hard?
- Would deleting or deepening the module reduce complexity rather than move it?

## Output

Return a small ranked set of candidates with affected paths/symbols, problem, evidence, proposed deepening, benefits to locality/testability, and recommendation strength. Do not create a new interface until the candidate is deliberately selected and designed with `codebase-design`.

Any chosen refactor must re-enter the normal intent -> context -> plan -> implementation -> verification -> review flow and use the existing provenance chain.
