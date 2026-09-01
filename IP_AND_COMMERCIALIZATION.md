# IP, Copy Protection, and Commercialization

## Current position

This repository is public and currently has no detected repository license. That is a legal state, not a technical copy-protection mechanism. Public GitHub repositories can be viewed and forked under GitHub's platform rules, so the project must not rely on obscurity or client-side controls to protect the core idea.

Do not add a restrictive or open-source license by automation. The copyright holder should choose the intended licensing model with appropriate legal advice.

## Recommended product boundary

Use an open-core or source-available distribution boundary rather than trying to make the local skill impossible to copy.

### Keep distributable

- Agent/CLI adapters and installation experience.
- Stable provider contract.
- Basic routing and policy interfaces.
- Local deterministic evaluation runner.
- Extension contracts for Graphify, code-mem, Superpowers, Ponytail, Caveman, and MCP providers.
- Documentation and reference examples.

### Keep commercially differentiated

- Hosted organization control plane.
- Private evaluation corpus and benchmark methodology.
- Organization-specific engineering memory and learned patterns.
- Cross-repository dependency/impact intelligence.
- Production outcome learning and regression intelligence.
- Enterprise policy packs and compliance controls.
- Premium integrations and managed connectors.
- Fleet-wide analytics for quality, cost, latency, regressions, and developer productivity.
- Support, rollout, architecture tuning, and migration services.

The objective is that a copied local implementation can still be useful, while the commercial system remains materially better because its value comes from continuously accumulated evidence, integrations, evaluation data, and organization-specific learning.

## Copy-protection guardrails

1. **Copyright and licensing**: explicitly choose and publish the legal terms before commercial distribution.
2. **Trademark**: protect the product name and visual identity separately from the source license.
3. **Private IP boundary**: do not commit private benchmark corpora, customer memories, proprietary prompts, credentials, signing keys, or commercial connector code to the public repository.
4. **Release provenance**: publish signed release artifacts and a machine-readable component manifest so users can distinguish official releases from modified copies.
5. **Brand provenance**: official releases should identify the project version, source commit, and release channel.
6. **Hosted moat**: keep high-value organization learning and fleet intelligence server-side where appropriate.
7. **Tenant isolation**: customer memory, learned policies, regression history, and evaluation results must be tenant-scoped and exportable.
8. **No hidden telemetry**: telemetry must remain explicit, configurable, documented, and off by default for sensitive customer environments.
9. **Dependency provenance**: record optional integrations and their licenses; never silently vendor third-party code.
10. **No security theater**: client-side license checks, obfuscated prompts, or hidden phone-home behavior are not considered protection and should not be introduced.

## Recommended commercial model

Start with a free local developer edition and charge for organizational value.

### Free

Local execution, basic orchestration, deterministic evals, and optional integrations.

### Pro / Team

Charge for hosted evaluation, organization memory, advanced impact analysis, regression intelligence, dashboards, shared policy packs, and team-level analytics.

### Enterprise

Charge for private deployment, SSO/RBAC, audit controls, data residency requirements, custom connectors, organization-specific evaluation suites, support, and onboarding.

### Services

Use paid pilots and architecture/rollout engagements to prove measurable improvement before committing to a large software contract.

## What creates the moat

The moat should not be the prompt text. Prompts and local orchestration logic can be reproduced.

The durable moat is:

`Repository evidence -> Outcome data -> Evaluation corpus -> Learned engineering patterns -> Better routing/retrieval/verification -> Better outcomes`

This feedback loop becomes stronger with every legitimate customer deployment while preserving customer isolation.

## Commercial proof requirement

Do not market the system as a productivity breakthrough until real repositories demonstrate it. Track at minimum:

- time to accepted change;
- first-pass acceptance rate;
- escaped regression rate;
- RCA precision and false-positive rate;
- tests added per accepted change;
- human review effort;
- model/tool calls;
- token and provider cost;
- latency;
- percentage of tasks completed without rework.

A credible product claim should compare the orchestrator against the same task performed with the team's normal coding-agent workflow.

This document is architectural/product guidance, not legal advice.
