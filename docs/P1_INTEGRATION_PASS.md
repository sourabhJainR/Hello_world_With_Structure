# P1 Integration Pass

This pass connects the P1 primitives into a deterministic task-state pipeline without coupling the core to an AI provider or optional knowledge system.

## Runtime path

```text
Task
  -> build_task_state()
  -> repository DNA snapshot
  -> apply_route()
  -> risk controls
  -> optional extension negotiation
  -> execution/verification evidence
  -> finalize_proof()
  -> regression seed when a failure is valuable
```

The pipeline is intentionally side-effect-light. It records coordination state; the host remains responsible for invoking the selected agent, repository-native tests, sandbox, worktree, and external providers.

## Why this boundary matters

P1 should improve the quality of every host rather than compete with Claude Code, Codex, Gemini, Graphify, code-mem or another agent runtime. Provider adapters can consume the state and proof artifacts while the core retains ownership of contracts, risk and evidence semantics.

## Acceptance gates

A task must not be marked proven solely because an agent returns successfully. Verification records must identify the check performed, and material decisions must reference evidence. Optional extension absence produces a degraded capability result rather than a hard dependency.

## Deterministic evaluation

Run:

```bash
python scripts/run_p1_evals.py
python -m unittest discover -s tests -v
```

CI also compiles the P1 runtime and executes the P0 and P1 suites.

## Current limitation

The repository environment used to author this pass does not provide network access for cloning the GitHub checkout or executing its GitHub Actions runner. The local execution gate therefore cannot truthfully report a full remote-suite result from this session. CI remains the authoritative full-repository execution environment.
