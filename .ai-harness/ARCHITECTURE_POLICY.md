# Architecture Policy

Repository structure is evidence, not automatic truth. Existing code may contain legacy patterns.

When multiple local patterns exist, choose the one that best balances:

- current task fit
- correctness and explicit contracts
- dependency direction
- cohesion and coupling
- testability
- scalability
- compatibility
- operational diagnosability
- consistency with the dominant maintained pattern

Prefer maintained, well-tested, recently used patterns over abandoned or isolated patterns.

Do not copy a local anti-pattern merely because it exists.

## Placement decision

Before adding a new source file, identify:

1. owning domain or feature;
2. architectural layer;
3. nearest maintained sibling implementations;
4. existing namespace/module/package convention;
5. test location convention;
6. candidate locations and rejected alternatives.

When the best choice differs from the dominant local pattern, record the deviation and reason in the run evidence.

## Invariants

Architecture rules should be expressed as enforceable dependency boundaries, naming rules, placement rules, and structural tests wherever practical. Prefer mechanical enforcement over prompt-only guidance.
