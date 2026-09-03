# Live Provider Telemetry and Turn Control

The provider bridge observes the provider process while it is running rather than reconstructing tool activity from the final answer.

## Runtime flow

`prompt -> provider stream -> raw JSONL journal -> normalization -> AgentTurnStateMachine -> live decision -> continue | interrupt`

Each invocation records state transitions, tool-call observations, provider token usage, provider cache usage, context page lineage and measurable decisions.

Tool observations contain a sequence, tool name, status, duration, call ID and digests of arguments/results. Raw provider events are retained in `<phase>.stream.jsonl` for adapter debugging.

Claude Code and Gemini CLI are invoked in their documented streaming JSON modes. Codex uses `codex exec --json`. Claude's tool-use contract and Gemini's `tool_use`/`tool_result` stream make the provider event boundary observable; Codex's JSONL stream supplies structured execution events. Unknown event shapes remain in the raw stream instead of being fabricated as known telemetry.

## Interruptible decision loop

For every completed or failed tool result, the bridge immediately:

1. journals the normalized `ToolObservation`;
2. updates token/cache state when the event contains it;
3. calls `AgentTurnStateMachine.decide_live()`;
4. journals `live.turn.decision`;
5. continues the provider only when the decision is `continue`;
6. terminates the provider process when the decision is `stop` or `repair`.

A tool that has already started cannot be retroactively cancelled through a generic stdout stream. The interruption occurs after the current provider event has been observed and before the provider can perform further model/tool work. On POSIX the provider is placed in its own process session so the harness can terminate the process group.

## Decision policy

Decision precedence is:

`tool failure -> repair`

`token budget exhausted -> stop`

`tool-call budget exhausted -> stop`

`insufficient measurable progress -> stop`

`live quality threshold -> stop`

`otherwise -> continue`

The policy uses observed tool results, result-digest diversity, provider token usage, failure count and configured budgets. It does not claim final verification while the provider turn is incomplete.

## Interrupt artifacts

- `live-interrupt.json` records the action, reason, utility, observed tool count and provider exit code.
- Exit code `75` means the current provider turn requested repair; the existing engine retry policy can start the next attempt with failure/new-evidence context.
- Exit code `76` means the current provider turn requested a deliberate stop.
- `live-agent-turns.jsonl` contains the live state/observation/decision journal.

## Cache truthfulness

Provider cache hits are only marked when provider usage reports cache-read tokens or explicit cache telemetry. A harness context-page cache hit is never presented as a model-provider KV-cache hit.

## Data handling

Tool arguments and results are represented by digests in structured telemetry. Raw provider streams may contain sensitive repository content and should follow normal run-directory retention and access controls.
