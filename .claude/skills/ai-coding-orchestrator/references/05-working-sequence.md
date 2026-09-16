# Working sequences and output discipline

## Normal coding

`understand intent -> repository map -> find reusable implementation -> acquire bounded context -> declare quality evidence -> choose execution strategy -> implement -> verify -> review -> integrate -> regression -> artifact -> shadow -> canary -> promote or rollback`

## Research / POC

`define question -> repository map -> bounded evidence -> research -> prototype when useful -> measure -> decide -> record unknowns -> normal implementation gates`

## Visual documentation

`audience -> repository map -> context/evidence -> typed topology -> validate -> standalone HTML -> inspect -> publish`

## Review

`acquire context -> inspect contracts and graph -> reproduce -> classify findings -> course-correct -> verify -> review`

## Skill composition

- `research`: acquire uncertain external/architectural evidence before implementation.
- `prototype`: use a bounded experiment when it resolves uncertainty faster.
- `resolving-merge-conflicts`: only for active merge/rebase conflicts; preserve intent and verify.
- `interactive-documentation`: produce portable visual architecture/workflow evidence.
- `retro`: turn verified session outcomes into small durable improvements.

Skills are orchestration surfaces that reuse canonical repository, context, evidence, and provenance stores.

## Output discipline

Report what changed, why, what was verified/reviewed, evidence/receipts, remaining uncertainty, reusable implementations inspected and reuse decisions, placement/dependency decisions, and relevant risks. Prefer concrete paths, symbols, tests, graph edges, snapshot digests, and lifecycle state over broad claims.
