# Agency Runtime v6

Use the Agency Runtime v6 lifecycle to make execution state explicit, bounded, and auditable.

## Lifecycle

`created -> planned -> executing -> verifying -> passed|failed|repairing|blocked`

Repair is bounded by `max_repairs`. When the repair budget is exhausted, the runtime escalates instead of retrying forever. Terminal states cannot transition.

## Provenance

Every lifecycle event is appended to an in-memory append-only ledger. Each event receives a deterministic hash-derived event ID and links to the preceding event ID. Do not place secrets, credentials, tokens, or raw sensitive payloads in event details.

## Execution contract

Agents may propose work, collect evidence, repair material findings, and report verification. The lifecycle remains the authority for state transitions. A successful outcome must reach `passed` through verification; missing evidence, blocked permissions, or exhausted repair budget must not be represented as success.

## Recovery

Use repair only for actionable findings. Use escalation when the repair budget is exhausted, an execution boundary is unavailable, or the host cannot safely continue. The host remains responsible for command execution, permissions, concurrency, and external side effects.
