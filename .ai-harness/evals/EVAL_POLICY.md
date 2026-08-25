# Evaluation Policy

The harness is evaluated as an engineering control plane, not only as a text generator.

## What evals measure

- Intent routing accuracy.
- Minimum-capability selection.
- Risk and uncertainty escalation.
- Extension selection without mandatory dependencies.
- Context-budget discipline, retrieval relevance, deduplication, and no unnecessary history replay.
- Session handoff fidelity without transcript replay.
- Independent verification quality and false-positive resistance.
- Repository-first behavior and verification requirements.
- Focused post-task entropy control.
- Skill metadata clarity and progressive disclosure.
- Safety invariants: no silent installation, permission escalation, production access, or autonomous looping.
- Outcome quality relative to total model calls, tokens, retries, latency, and cost when telemetry is available.

## Evaluation classes

1. Deterministic routing: fast, dependency-free, suitable for CI.
2. Policy checks: inspect skill/config/manifest invariants.
3. Context checks: verify bounded context, relevance, deduplication, and evidence preservation.
4. Session checks: verify compact durable handoffs and safe rehydration behavior.
5. Verification checks: verify fresh-context review for material work and anti-false-positive reasoning.
6. Integration evals: run only when the corresponding optional extension is installed.
7. Model evals: optional provider-backed tests; never required for a green core build.

## Scoring

Each case has a required mode and capability set. A case passes when the predicted mode matches and every required capability is selected. Extra capabilities are reported as an efficiency warning rather than an automatic failure unless the case marks them as forbidden.

The suite reports accuracy, unnecessary-capability rate, safety-policy failures, and context-efficiency signals separately. A release must have zero safety-policy failures and zero invalid skill metadata/configuration failures.

Token reduction is never treated as a quality win by itself. A change that lowers token use but increases retries, verification failures, or task failures is a regression.

## Context-bloat rule

The canonical skill is intentionally concise. Detailed operating guidance belongs in reference files and should be loaded only when relevant. Duplicated skill copies must remain semantically aligned and must not independently grow large.

Always-loaded instructions should contain only information that is mandatory and non-obvious. Repository facts that can be discovered reliably should not be duplicated into global instructions.

## Evolution

Add a regression case whenever a routing, extension, context, session, verification, safety, or skill-discovery defect is found. Do not tune routing only to the current cases; include adversarial and negative cases to reduce overfitting.

Any proposed self-improvement must be evaluated against a stable baseline before promotion. Learned observations may recommend changes but cannot silently modify executable policy.
