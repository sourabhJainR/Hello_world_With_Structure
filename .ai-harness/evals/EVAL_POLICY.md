# Evaluation Policy

The harness is evaluated as an engineering control plane, not only as a text generator.

## What evals measure

- Intent routing accuracy.
- Minimum-capability selection.
- Risk and uncertainty escalation.
- Extension selection without mandatory dependencies.
- Context-budget discipline and no unnecessary history replay.
- Repository-first behavior and verification requirements.
- Skill metadata clarity and progressive disclosure.
- Safety invariants: no silent installation, permission escalation, production access, or autonomous looping.

## Evaluation classes

1. Deterministic routing: fast, dependency-free, suitable for CI.
2. Policy checks: inspect skill/config/manifest invariants.
3. Context checks: verify bounded context and evidence preservation.
4. Integration evals: run only when the corresponding optional extension is installed.
5. Model evals: optional provider-backed tests; never required for a green core build.

## Scoring

Each case has a required mode and capability set. A case passes when the predicted mode matches and every required capability is selected. Extra capabilities are reported as an efficiency warning rather than an automatic failure unless the case marks them as forbidden.

The suite reports accuracy, unnecessary-capability rate, and safety-policy failures separately. A release must have zero safety-policy failures and zero invalid skill metadata/configuration failures.

## Context-bloat rule

The canonical skill is intentionally concise. Detailed operating guidance belongs in reference files and should be loaded only when relevant. Duplicated skill copies must remain semantically aligned and must not independently grow large.

## Evolution

Add a regression case whenever a routing, extension, context, safety, or skill-discovery defect is found. Do not tune routing only to the current cases; include adversarial and negative cases to reduce overfitting.
