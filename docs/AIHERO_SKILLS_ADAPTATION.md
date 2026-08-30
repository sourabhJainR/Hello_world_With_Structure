# AI Hero Skills Adaptation Review

## Source and license

This project reviewed the AI Hero skills catalog and its upstream repository, `mattpocock/skills`.

The upstream repository declares the MIT License. General workflow ideas are adapted here; this project does not copy the upstream skill set wholesale. Any future substantial copying of upstream text must retain the required MIT attribution and license notice.

## What strengthens this ecosystem

### Small, composable disciplines

Keep the orchestrator as a control plane. Use focused disciplines only when routing shows they add evidence.

### Explicit invocation boundaries

Separate user-invoked workflows from model-invoked reference disciplines to avoid accidental context injection.

User workflows:

`grill -> spec -> slices -> implement -> review`

Reference disciplines:

`domain-modeling, codebase-design, TDD, regression safety, architecture quality, context efficiency`

Skip stages that do not add evidence.

### Specification as a decision record

Do not invent requirements to fill templates. Preserve settled decisions, explicit assumptions, non-goals, acceptance criteria, risks, and verification requirements.

### Domain language

For domain-heavy work, challenge vague or overloaded terms and keep canonical vocabulary aligned with repository behavior.

### Deep modules and seams

Prefer substantial behavior behind small stable interfaces. Reuse existing seams where possible. New abstractions must reduce coupling or improve verification.

### Vertical slices and TDD

Use independently verifiable behavior slices. Prefer red-green-refactor where deterministic behavior and a stable seam exist; do not force TDD where it adds ceremony without improving evidence.

### Disciplined diagnosis

Use:

`reproduce -> minimize -> rank hypotheses -> instrument -> prove cause -> fix -> regression test`

Do not jump directly from symptom to fix.

### Throwaway prototypes

A POC must state its uncertainty, success/failure threshold, resource boundary, and whether its code is disposable. Prototype code cannot silently become production code.

### Two-axis review

Review:

1. **Spec/Contract:** required behavior and boundaries.
2. **Repository/Engineering:** local standards, architecture, operations, observability, and regressions.

Prefer independent review context for meaningful/high-risk work.

### Durable handoff

Persist:

`TASK, CONTRACT, DONE, OPEN, EVIDENCE, RISKS, NEXT`

Do not replay full transcripts.

## What this project should retain beyond the upstream pattern

- provider-neutral orchestration;
- Graphify/code-mem as optional evidence providers;
- provenance and evidence ranking;
- token, call, latency, and retry economics;
- regression and behavior-preservation gates;
- phase-aware architecture evolution;
- operational discipline and observability checks;
- extension contracts and graceful degradation;
- deterministic evals and safe learning boundaries.

## What not to adopt blindly

Do not make these defaults:

- a fixed workflow for every task;
- mandatory issue-tracker publication;
- mandatory sub-agents;
- mandatory TDD;
- repository-wide cleanup during normal implementation;
- large always-loaded context files.

## Maintenance rule

When upstream skills evolve, review each practice by problem solved, overlap with current behavior, context cost, determinism gain, provider neutrality, and regression evidence required.

The governing rule:

> Use the smallest process that produces sufficient evidence for a safe, high-quality engineering outcome.
