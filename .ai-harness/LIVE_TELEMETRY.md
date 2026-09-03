# Live Provider Telemetry

The provider bridge observes the provider process while it is running rather than reconstructing tool activity from the final answer.

## Runtime flow

`prompt -> provider stream -> raw JSONL journal -> normalization -> AgentTurnStateMachine -> live-agent-turns.jsonl`

Each invocation records state transitions, tool-call observations, provider token usage, provider cache usage, context page lineage and measurable completion decisions.

Tool observations contain a sequence, tool name, status, duration, call ID and digests of arguments/results. Raw provider events are retained in `<phase>.stream.jsonl` for adapter debugging.

Claude Code and Gemini CLI are invoked in their documented streaming JSON modes. Claude emits streaming content-block events for tool calls and result/usage data; Gemini emits JSONL events including `tool_use`, `tool_result`, and result statistics. The adapter preserves unrecognized events rather than inventing telemetry.

Provider cache hits are only marked when provider usage reports cache-read tokens or explicit cache telemetry. Otherwise the state machine records `harness-context-only`.

The live journal is kept separate from the existing phase-level compatibility summary so existing run artifacts remain stable.

Tool arguments and results are represented by digests in structured telemetry. Raw provider streams should follow normal run-directory retention and access controls for sensitive repositories.
