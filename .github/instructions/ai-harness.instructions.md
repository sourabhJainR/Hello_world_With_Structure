---
applyTo: ".ai-harness/**/*.py,.ai-harness/**/*.toml,.ai-harness/**/*.md"
---

When changing the harness itself, preserve provider neutrality and dependency direction. Prefer the existing module boundary and pattern before creating a new abstraction.

Required review lenses: state/lifecycle correctness, intent and scope integrity, provider isolation, optional-extension degradation, compatibility, deterministic behavior, persistence durability, failure/cancellation semantics, security, observability, and tests/evals.

Do not hard-code release/configuration versions in tests or workflows when the value can be derived from the authoritative configuration. Add deterministic regression coverage for material behavioral changes.

Do not weaken verification or safety gates to make a check pass. Fix the root cause and retain the invariant.
