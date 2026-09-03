# Planning phase

This phase is read-only. Do not edit, create, delete, rename, format, commit, or otherwise mutate repository files.

Explore only the evidence needed to produce an implementation plan for the current task. Identify:

1. the exact repository constructs affected;
2. the existing maintained patterns to reuse;
3. the smallest safe change set;
4. compatibility and failure-path considerations;
5. tests/evals and verification evidence required;
6. risks, assumptions, and unresolved questions;
7. a reversible implementation sequence.

Return a concise plan with explicit file/construct references. Mark unresolved constructs as `UNRESOLVED CONSTRUCT` rather than guessing.

The next implementation phase must follow this plan unless new evidence proves a material change is necessary. If the plan becomes invalid, stop and re-plan rather than silently changing direction.
