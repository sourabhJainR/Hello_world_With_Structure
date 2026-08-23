# Execution and Safety Policy

Autonomy is capability-scoped.

## Capability levels

### Observe
Read repository files, history, configuration, tests, logs, and local artifacts.

### Analyze
Research, compare designs, generate plans, inspect failures, and review changes. No mutation.

### Mutate
Edit source, tests, configuration, documentation, and local tooling inside the approved workspace.

### Operate
Run builds, tests, local services, migrations against disposable environments, and controlled developer tools.

### Promote
Push branches, open pull requests, merge, deploy, or perform irreversible external actions.

Observe/Analyze are default. Mutate/Operate require an explicitly selected execution phase. Promote requires explicit policy approval and must never be inferred from task wording alone.

## Isolation

Use a dedicated worktree for high/critical risk, long-running, experimental, or parallel mutating work.

Keep credentials and external systems outside the agent workspace unless specifically required and approved.

## Command safety

Prefer argv-based execution. Avoid shell interpolation, dynamic command construction, credential exposure, destructive commands, and unbounded process execution.

Every command must have a timeout and captured result.

## External side effects

Classify side effects as:

- none
- local/disposable
- reversible external
- irreversible external

The last class requires explicit human approval.

## Recovery

A failed operation must preserve its evidence. Do not automatically clean up or destroy a failed worktree before review unless the configured policy explicitly allows it.
