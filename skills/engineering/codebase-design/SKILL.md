---
name: codebase-design
description: Design maintainable module shapes using depth, locality, seams, interfaces, and adapters without adding speculative layers.
---

# Codebase Design

Use this vocabulary consistently: module, interface, depth, seam, adapter, locality, and leverage.

## Design test

A deep module hides substantial complexity behind a small interface. Apply the deletion test: if removing the candidate module would merely move complexity elsewhere, it is probably shallow.

Before adding an abstraction, find the existing owner and compare at least two plausible designs when the seam itself is uncertain. Prefer the design with better locality, fewer concepts exposed to callers, clearer ownership, and easier behavioral testing.

## Repository rules

Respect existing ADRs and module boundaries. Do not rename concepts merely to mirror an external framework. Reuse the repository's canonical context, provenance, execution, and capability contracts.

One adapter should represent a real hypothetical seam; repeated adapters around the same responsibility are evidence that the owner should deepen instead.

## Output

For an architecture change, state the current seam, the proposed seam, what complexity moves behind it, callers affected, compatibility strategy, and verification seam. Design work is not complete until the implementation can be exercised through a stable public interface.
