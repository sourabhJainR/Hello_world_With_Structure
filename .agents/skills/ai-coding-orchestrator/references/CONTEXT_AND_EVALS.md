# Context and Evals

Keep the skill metadata and always-needed instructions short. Load detailed references only when needed. Retrieve repository evidence in bounded tiles and rank before inclusion. Prefer symbols, signatures, graph paths, focused diffs, current failures, and compact decisions over full files or transcripts. Preserve verification evidence losslessly.

Use `.ai-harness/evals/cases.jsonl` and `scripts/run_evals.py` for deterministic routing and policy checks. Add a regression case for routing, context, extension, safety, or skill-discovery defects. Keep core evals dependency-free; provider-backed/model evals are optional.
