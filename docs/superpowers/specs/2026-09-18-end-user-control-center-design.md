# End-User Control Center Design

## Goal

Make AER easier to operate day to day without changing its core execution ownership: a user should be able to install AER, see whether it is healthy, understand what is active, inspect background work and learning state, and diagnose common setup problems from one stable CLI.

## User experience

The control-center surface adds five read-only commands:

- `status` shows the active AER build, installed skill surfaces, provider availability, background trigger counts, durable sessions, and the latest engineering report for an optional project.
- `doctor` validates the active installation, state databases, skill synchronization, provider discovery, and optional project paths. It exits non-zero only for actionable errors; warnings remain visible but do not fail the command.
- `sessions` shows recoverable durable checkpoints with task, stage, provider, attempt, update time, and a safe resume hint.
- `trigger-status <id>` shows the durable lifecycle of a background LLM trigger without requiring the user to inspect SQLite.
- `learning` shows the current advisory adaptive policy and recent maintenance receipts so users can see whether learning is active without reading internal databases.

All commands support `--json` for IDEs, CI, or future UI clients.

## Architecture

Add one dependency-free diagnostics module, `portable/aer_diagnostics.py`. It is read-only and composes existing owners:

- `SessionStore` remains the session owner.
- `AutomationScheduler` / `TriggerRuntime` remain the background-work owners.
- `AdaptiveTuner` remains the learning-policy owner.
- `PersistentMemory` remains the memory owner.

The diagnostics layer may execute read-only SQL for aggregation where no public query exists, but it must never create a second source of truth or mutate state.

Extend `portable/aer_runtime.py` only to route CLI subcommands to diagnostics functions. Existing build, verify, install, update, check-update, and rollback behavior remains unchanged.

## Safety and compatibility

- Diagnostics are read-only.
- No command changes credentials, permissions, MCP configuration, repository files, schedules, learning policy, or approval state.
- Existing persisted JSON/SQLite formats remain compatible.
- Missing optional providers are reported as warnings, not hard failures.
- Corrupt or unreadable optional state is surfaced as a diagnostic error with a bounded message.
- JSON output is stable enough for automation: top-level `command`, `status`, and `items`/domain fields are present.

## Success criteria

A new user can run `python aer_cli.py status` and immediately understand the installed build and whether the local AER state is usable.

A user can run `python aer_cli.py doctor --json` and identify actionable installation/state/provider problems without opening implementation files.

A background trigger ID returned by the LLM trigger path can be inspected with `trigger-status`.

A completed session checkpoint and current adaptive policy are visible through the CLI without direct database/file inspection.

The complete deterministic test suite continues to pass, and the portable bundle includes the diagnostics module and CLI behavior.
