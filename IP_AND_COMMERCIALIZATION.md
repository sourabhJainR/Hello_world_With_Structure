# IP, Copy Protection, and Commercialization

## Current position

The plugin metadata currently declares `MIT`, but the repository has no root `LICENSE` file. Treat this as a release-blocking licensing inconsistency, not as proof of a chosen legal model. Resolve the intended license with the copyright holder before public distribution or commercialization.

This repository is public. Do not rely on obscurity, obfuscation, client-side license checks, or hidden phone-home behavior to prevent copying.

## Recommended product boundary

Use an open-core or source-available boundary rather than trying to make the local skill impossible to copy.

### Keep distributable

- Agent/CLI adapters and installation experience.
- Stable provider contract.
- Basic routing and policy interfaces.
- Local deterministic evaluation runner.
- Extension contracts for Graphify, code-mem, Superpowers, Ponytail, Caveman and MCP providers.
- Documentation and reference examples.

### Keep commercially differentiated

- Hosted organization control plane.
- Private evaluation corpus and benchmark methodology.
- Organization-specific engineering memory and learned patterns.
- Cross-repository dependency/impact intelligence.
- Production outcome learning and regression intelligence.
- Enterprise policy packs and compliance controls.
- Premium integrations and managed connectors.
- Fleet analytics for quality, cost, latency, regressions and developer productivity.
- Support, rollout, architecture tuning and migration services.

The commercial system should remain materially better because its value comes from accumulated evidence, integrations, evaluation data and organization-specific learning rather than secret prompt text.

## Copy-protection guardrails

1. Explicitly choose and publish legal licensing terms.
2. Protect product name, logo and official distribution identity separately from source licensing.
3. Keep private benchmark corpora, customer memories, credentials, signing keys and commercial connector code out of the public repository.
4. Publish official release provenance: version, source commit, artifact digest and dependency/component manifest.
5. Keep organization learning and fleet intelligence server-side where appropriate.
6. Tenant-scope customer memory, learned policies, regression history and evaluation results.
7. Keep telemetry explicit, configurable, documented and off by default for sensitive environments.
8. Record optional integrations and their licenses; never silently vendor third-party code.
9. Do not add obfuscation, hidden telemetry or anti-debugging as a supposed moat.

## Recommended commercial model

Start with a free local developer edition and charge for organizational value.

### Free

Local execution, core orchestration, deterministic evals and optional integrations.

### Pro / Team

Hosted evaluation, organization memory, advanced impact analysis, regression intelligence, dashboards, shared policy packs and team analytics.

### Enterprise

Private deployment, SSO/RBAC, audit controls, data residency, custom connectors, organization-specific evaluation suites, support and onboarding.

### Services

Paid pilots and architecture/rollout engagements should prove measurable improvement before a large software contract.

## Durable moat

`Repository evidence -> Outcome data -> Evaluation corpus -> Learned engineering patterns -> Better routing/retrieval/verification -> Better outcomes`

This feedback loop should strengthen with legitimate customer use while preserving tenant isolation.

## Commercial proof requirement

Do not market a productivity breakthrough until real repositories demonstrate it. Track:

- time to accepted change;
- first-pass acceptance rate;
- escaped regression rate;
- RCA precision and false-positive rate;
- tests added per accepted change;
- human review effort;
- model/tool calls;
- token/provider cost;
- latency;
- percentage of tasks completed without rework.

Compare against the same tasks performed with the team's normal coding-agent workflow.

This document is architectural/product guidance, not legal advice.
