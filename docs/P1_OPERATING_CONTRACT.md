# P1 Operating Contract

P1 turns the P0 contracts into reusable intelligence without making optional integrations mandatory.

## Repository DNA

Maintain a compact repository profile with explicit/observed/inferred/unknown status and evidence IDs. Recompute only fields affected by changed paths. Never let inferred conventions override explicit repository instructions.

## Regression Genome

Every high-value failure or correction can become a deterministic regression case. Cases must be stable, bounded, reviewable, and free of secrets. Promotion into mandatory policy requires human review or an explicitly configured organization policy.

## Engineering Memory Graph

Represent durable engineering relationships as small nodes and evidence-backed edges. Prefer facts and decisions over transcript storage. External memory systems such as code-mem remain optional providers.

## Proof Graph

Connect requirement, evidence, decision, change, verification, review, and outcome. A missing link is a visible gap, not an invented relationship.

## Extension capability negotiation

Optional providers advertise capabilities. The core selects only the capabilities it needs and must degrade safely when providers are absent or fail. No extension may silently replace core policy.

## Host/provider boundary

Core state, contracts, evidence, risk, verification, and policy remain provider-neutral. Claude, Codex, Gemini, Graphify, code-mem, Ponytail, Superpowers, Caveman, MCP and similar systems are adapters/extensions, not prerequisites.

## P1 acceptance criteria

1. Repository profiles are provenance-aware and selectively invalidated.
2. Regression cases are deterministic and repeatable.
3. Memory/proof graph relationships carry evidence references.
4. Optional providers negotiate capabilities and degrade safely.
5. Core behavior remains usable with zero optional extensions.
6. P1 runtime has unit/eval coverage and no new third-party dependency.
7. Documentation explains how each artifact affects real coding workflows.
