# Context and Evals

## Context discipline

Keep the skill metadata and always-needed instructions short. Load detailed references only when the task needs them. Retrieve repository evidence in bounded tiles and rank before inclusion. Prefer symbols, signatures, graph paths, focused diffs, current failures, and compact decisions over full files or transcripts. Verification evidence is lossless and must never be compressed away.

## Eval discipline

Use `.ai-harness/evals/cases.jsonl` and `scripts/run_evals.py` for deterministic routing and policy checks. Add a regression case for every routing, extension, safety, context, or skill-discovery defect. Include negative cases that test unnecessary capability selection.

Core evals should remain dependency-free and fast. Optional provider-backed evals may be added separately and must never be required for core installation.

## Quality gates

A release requires:

- all deterministic eval cases passing;
- zero safety-policy failures;
- valid plugin/marketplace metadata;
- aligned skill copies;
- context budget within policy;
- repository test suite passing in CI.
