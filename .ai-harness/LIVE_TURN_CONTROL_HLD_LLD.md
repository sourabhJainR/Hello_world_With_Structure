# Live Turn Control — HLD and LLD

## 1. Purpose

This document describes the actual runtime path used by the repository for provider execution, live tool-call telemetry, context lineage, token/cache accounting, and interruptible stop/repair decisions.

The design goal is not to infer what happened after a provider exits. The provider process is streamed while it is executing. A normalized tool result becomes an observation, the `AgentTurnStateMachine` evaluates the evidence immediately, and the harness can terminate the provider before it requests or executes another model/tool step.

## 2. Important boundary

The harness does not execute a provider's internal tool implementation. Claude Code, Codex CLI, or Gemini CLI remains responsible for its own agent loop and tools. The harness owns the outer provider process boundary and can observe provider-native JSON events as they arrive.

Therefore:

`model -> provider internal tool execution` remains provider-owned.

`provider event -> harness observation -> live decision -> process continuation/interruption` is harness-owned.

A live stop is enforced after the current observable event has arrived. If the provider has already started a tool, the harness cannot retroactively cancel that tool through a generic CLI stdout stream; it terminates the provider process after the event. Provider-native hooks/API integrations can provide finer-grained pre-tool blocking where supported.

## 3. Actual end-to-end flow

```text
CLI: python .ai-harness/run.py run --task ...
  |
  v
run.py: optimized_run_task
  |
  v
engine.py: run_task
  |
  +--> route_with_provider
  |      |
  |      +--> build route.prompt.md
  |      +--> invoke
  |             |
  |             v
  |        provider.py
  |
  +--> phases_for -> context/research/execute/validate/review/learn
  |
  +--> build_prompt
  |      |
  |      +--> context_engine.flash_context_prompt
  |      +--> context page IDs + context_digest
  |      +--> knowledge_fabric.collect
  |      +--> intent contract + capability plan
  |
  v
engine.py: invoke(provider, prompt_file, phase, run_dir, timeout, ...)
  |
  v
configured provider command
  |
  +--> Python .ai-harness/provider.py --prompt-file ... -- claude -p
  +--> Python .ai-harness/provider.py --prompt-file ... -- codex exec
  +--> Python .ai-harness/provider.py --prompt-file ... -- gemini -p
  |
  v
provider.py: streaming_command
  |
  v
subprocess.Popen(provider CLI, stdout=PIPE, stderr=STDOUT, start_new_session=True)
  |
  v
provider JSONL event
  |
  +--> normalize_tool_event
  +--> normalize_usage
  +--> normalize_cache
  +--> transcript_text
  |
  v
AgentTurnStateMachine
  |
  +--> observe_tool / observe_usage / observe_cache
  |
  +--> live decision after tool_result or usage event
  |
  +---- continue --> provider remains alive
  |
  +---- stop ----> SIGTERM/process terminate -> live-interrupt.json -> terminal stopped
  |
  +---- repair --> SIGTERM/process terminate -> live-interrupt.json -> terminal repair interruption
  |
  v
engine.py receives provider exit code
  |
  +--> normal 0: phase succeeds
  +--> 75: existing phase retry path can perform repair attempt
  +--> 76: live stop is a hard interruption signal
  |
  v
run artifacts: <phase>.stream.jsonl, live-agent-turns.jsonl, live-interrupt.json
```

## 4. HLD components

| Component | Actual file | Responsibility | Key methods/functions |
|---|---|---|---|
| CLI/orchestrator entry | `.ai-harness/run.py` | Adds repository-specific orchestration around `engine` | `optimized_build_prompt`, `_observe_agent_turns`, `optimized_run_task` |
| Core execution coordinator | `.ai-harness/engine.py` | Creates run, routes task, builds phases, invokes providers, validates, retries, checkpoints | `run_task`, `invoke`, `route_with_provider`, `build_prompt`, `run_validation`, `repair_after_failure` |
| Provider process adapter | `.ai-harness/provider.py` | Converts provider CLI execution into streaming machine-readable events and owns live process interruption | `streaming_command`, `normalize_tool_event`, `normalize_usage`, `normalize_cache`, `interrupt_provider`, `main` |
| Live turn policy/state | `.ai-harness/runtime/agent_turn.py` | Provider-neutral state transitions, observations, token/cache state, measurable decisions | `AgentTurnStateMachine.transition`, `observe_tool`, `observe_usage`, `observe_cache`, `decide_live`, `decide`, `finish` |
| Context selection | `.ai-harness/context_engine.py` | Builds bounded IO-aware context and context-page lineage | `flash_context_prompt`, repository context/page selection functions |
| Context page cache | `.ai-harness/runtime/context_cache.py` | Content-addressed page reuse and pagination | `ContextPageCache.put`, `page`, `paginate`, `select`, `stats` |
| Loop policy | `.ai-harness/runtime/loop_engine.py` | Higher-level iteration planning and post-iteration action | `loop_plan`, `iteration_record`, `next_action` |
| Intent safety | `.ai-harness/runtime/intent_contract.py` | Prevents task drift | `create_intent_contract`, `semantic_alignment`, `verify_intent_contract` |
| Knowledge | `.ai-harness/knowledge_fabric.py` | Structural/external knowledge collection | `collect` |
| Lifecycle | `.ai-harness/p1_lifecycle.py` | Durable run lifecycle/checkpoint artifacts | `start`, `finish` |
| Capability selection | `.ai-harness/runtime/capability_catalog.py` | Selects/validates specialist capability plan | `select_capabilities`, `validate_plan` |
| Learning | `.ai-harness/runtime/learning.py` | Converts verified run evidence into learned observations | `evolve_run`, `trusted_advice` |

## 5. LLD — live event processing

### 5.1 Provider command construction

`engine.provider_command()` expands these exact placeholders:

- `{prompt_file}` -> phase prompt path
- `{workspace}` -> repository root
- `{phase}` -> phase name
- `{run_dir}` -> run artifact directory
- `{python}` -> current Python interpreter

Configured commands in `.ai-harness/config.toml` are:

- Claude: `{python} .ai-harness/provider.py --prompt-file {prompt_file} -- claude -p`
- Codex: `{python} .ai-harness/provider.py --prompt-file {prompt_file} -- codex exec`
- Gemini: `{python} .ai-harness/provider.py --prompt-file {prompt_file} -- gemini -p`

`provider.py:streaming_command()` adds the provider-specific structured-output mode only when it is not already present:

- Claude: `--output-format stream-json --verbose --include-partial-messages`
- Gemini: `--output-format stream-json`
- Codex: `--json`

These modes are provider-native streaming interfaces. Claude documents structured tool-use blocks and a tool loop keyed by `stop_reason`; Gemini documents `tool_use`, `tool_result`, and `result` JSONL events; Codex documents `codex exec --json` as JSONL output for automation. See the external references below.

### 5.2 Process isolation and termination

`provider.py:main()` uses `subprocess.Popen` instead of `subprocess.run` so the harness can consume stdout incrementally.

On POSIX, `start_new_session=True` creates a separate process session. `interrupt_provider()` sends `SIGTERM` to the provider process group and falls back to `process.terminate()` if necessary; after five seconds it escalates to `process.kill()`.

This is deliberate process-boundary control, not a claim that the harness can cancel an already executing provider-internal tool through an API it does not own.

### 5.3 Event normalization

`normalize_tool_event(row, sequence)` maps provider-specific shapes into:

```text
sequence
 tool
 status
 duration_ms
 result_digest
 error
 metadata.provider_event
 metadata.call_id
 metadata.arguments_digest
```

The original arguments/results are not persisted into the normalized telemetry record; only stable digests are stored. The raw provider JSONL is retained in `<phase>.stream.jsonl` for forensic/replay analysis.

### 5.4 Live state transitions

Normal provider execution starts:

`idle -> planning -> acting`

When a tool event arrives:

`acting -> observing`

For a completed/failed tool result:

`observing -> deciding`

Then:

- `deciding -> acting` for `continue`
- `deciding -> repairing -> stopped` for `repair`
- `deciding -> stopped` for `stop`

The provider is interrupted only after the normalized tool result has been journaled and the decision has been journaled.

### 5.5 Live decision inputs

`AgentTurnStateMachine.decide_live()` uses only information available at decision time:

- completed tool observation count
- failed/error observation count
- unique result digests as an evidence/progress proxy
- provider-reported token usage when available
- configured maximum tool calls
- configured maximum tokens
- previous utility and minimum progress gain
- current event type

It deliberately does not assign final verification to an unfinished provider turn.

Decision precedence:

1. observed tool failure -> `repair`
2. token budget exhausted -> `stop`
3. tool-call budget exhausted -> `stop`
4. insufficient live progress -> `stop`
5. live quality threshold -> `stop`
6. otherwise -> `continue`

### 5.6 Repair semantics

A live repair decision terminates the current provider process with exit code `75` and writes `live-interrupt.json`.

The existing `engine.run_task()` retry path already treats a non-zero provider exit as an attempt failure and can build the next attempt prompt with:

`Previous attempt failed. Gather new evidence and change the approach.`

This means the live layer does not create a second competing repair scheduler. It hands control back to the existing phase retry policy.

A future provider-specific integration can replace process restart with a native conversation/session continuation where that provider exposes an API for it.

### 5.7 Stop semantics

A live stop terminates the provider with exit code `76` and records the decision. `live-interrupt.json` is the durable source of truth for why the turn was interrupted.

The current engine has a legacy phase-retry loop around `invoke()`. The next hardening step should make `76` a first-class `STOPPED_BY_POLICY` result in `engine.run_task()` so the engine does not spend a retry slot after a deliberate stop. The current provider boundary already prevents additional provider tool/model work after the stop decision.

## 6. Context lineage

`run.py:optimized_build_prompt()` calls `context_engine.flash_context_prompt()` and stores its metadata in `_context_metadata[phase]`.

The prompt ends with:

`## IO-aware context`

followed by the metadata object containing the selected context/page information.

`provider.py:prompt_context()` extracts:

- `pages`
- `context_digest`

and passes them to `AgentTurnStateMachine.set_context()`.

Every turn therefore has an explicit relationship to the context pages used to produce its actions.

## 7. Token and cache telemetry

`normalize_usage()` recognizes provider usage aliases including:

- `input_tokens`
- `input_token_count`
- `output_tokens`
- `output_token_count`
- `cache_read_input_tokens`
- `cached_content_token_count`
- `thoughts_token_count`
- `total_tokens`
- `total_token_count`

`normalize_cache()` uses explicit provider cache fields or provider usage fields. A cache hit is never inferred from a harness page-cache hit.

When provider usage is absent, `AgentTurnStateMachine.observe_usage()` uses deterministic character/4 estimation and marks `estimated=true`.

## 8. Artifacts and their exact meanings

| Artifact | Meaning |
|---|---|
| `<phase>.prompt.md` | Exact prompt sent to the provider bridge |
| `<phase>.output.md` | Provider output captured by the existing engine phase contract |
| `<phase>.stream.jsonl` | Raw provider JSONL stream, written incrementally |
| `agent-turns.jsonl` | Live state/observation/decision journal during provider execution |
| `live-agent-turns.jsonl` | Renamed live turn journal retained as the compatibility-facing live artifact |
| `live-interrupt.json` | Exact live stop/repair decision and process interruption metadata |
| `manifest.json` | Run-level orchestration state and validation information |
| `checkpoint.json` | Phase-level resumability checkpoint |
| `execution-checkpoint.json` | Execution-control checkpoint |
| `loop-plan.json` | Bounded loop strategy and budget |
| `loop-outcome.json` | Higher-level post-phase loop outcome |
| `knowledge.json` / `knowledge.md` | Collected structural/external knowledge |
| `intent-contract.json` | Immutable task contract for drift detection |
| `capability-plan.json` | Selected specialist capabilities |

## 9. External tools and commands actually used by this codebase

### Provider CLIs

- `claude` — configured as `claude -p`; streaming JSON is requested by `provider.py`.
- `codex` — configured as `codex exec`; JSONL is requested with `--json`.
- `gemini` — configured as `gemini -p`; streaming JSON is requested with `--output-format stream-json`.

### Repository/process tools invoked by `engine.py`

- `git status --short`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git diff --stat`
- `git diff --check`
- `git diff --name-only`
- `git ls-files --cached --others --exclude-standard`

### Project profile

- `python <repo>/.ai-harness/project_profile.py`

### Optional knowledge tools declared in config

- `graphify` — optional; configured artifact paths `graphify-out/graph.json` and `.graphify/graph.json`.
- `codebase-memory-mcp` — optional; configured artifact `.codebase-memory/graph.json`.
- semantic reranker — disabled by default.

### Validation commands auto-discovered by `engine.run_validation()`

- `npm test --if-present` when `package.json` exists
- `go test ./...` when `go.mod` exists
- `cargo test` when `Cargo.toml` exists
- `dotnet test --nologo` when `.sln` or `.csproj` exists
- `python -m pytest -q` when `pyproject.toml`/`pytest.ini` exists and Python test files are found

Only configured/auto-discovered commands are run; the engine caps validation command execution at five commands.

## 10. Database, stored procedures, and SQL query inventory

No SQL statements, stored-procedure invocations, ORM query definitions, or database client calls were found in the repository paths inspected for this implementation.

There is therefore no actual SP/query execution path in this harness today. The codebase's external execution surface is process/CLI based rather than database based.

If a future repository extension adds SQL/database access, it should be added to this inventory with the exact client, connection boundary, query/stored-procedure name, parameters, result shape, timeout, and telemetry event rather than being described generically as a "query".

## 11. Security and correctness controls

- Tool/result payloads are hashed for normalized telemetry; raw provider output remains available for audit.
- Provider-native cache telemetry is trusted only when explicitly reported.
- Context page IDs and digest are recorded before provider execution.
- Process termination is scoped to a dedicated POSIX process session where available.
- RCA/analysis-only prompts modify provider permissions to plan/read-only modes through `analysis_only_command()`.
- No shell-string interpolation is introduced; subprocess commands remain argument arrays.
- Provider output is treated as untrusted data; unknown JSON event shapes are retained in the raw stream instead of being fabricated as known telemetry.

## 12. Known limitations

1. Generic CLI streaming cannot prevent a provider from completing a tool that has already started. It can prevent subsequent model/tool work by terminating the provider process after the result event.
2. Provider token usage may be cumulative at the provider-turn level rather than per tool call. The harness records the provider's reported granularity without pretending it is finer.
3. Provider event schemas can evolve. `normalize_tool_event()` deliberately supports aliases and retains unknown events in the raw stream.
4. Native provider hooks are richer than a generic stdout bridge. Gemini exposes `BeforeTool`/`AfterTool` hooks that can block/stop an agent loop; Claude's API exposes explicit `tool_use`/`tool_result` round trips for client-executed tools. These are candidates for future adapters, not assumptions in the generic bridge.
5. `INTERRUPT_STOP_EXIT=76` should become a first-class engine outcome in the next hardening patch to avoid consuming a legacy retry slot after a deliberate live stop.

## 13. External references used for design validation

- Claude tool-use loop and `tool_use` / `tool_result`: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- Claude tool-call handling: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
- Gemini headless streaming JSON: https://geminicli.com/docs/cli/headless/
- Gemini hooks and `BeforeTool`/`AfterTool`: https://geminicli.com/docs/hooks/reference/
- Gemini tool reference: https://geminicli.com/docs/reference/tools/
- Codex `exec --json` JSONL: https://www.mintlify.com/openai/codex/cli/exec
- Python `subprocess.Popen`, `start_new_session`, `terminate`, and process groups: https://docs.python.org/3/library/subprocess.html

## 14. Naming rules used by this implementation

The following names are intentionally aligned to their actual responsibility:

- `AgentTurnStateMachine` — owns state transitions for one provider turn.
- `ToolObservation` — one normalized observed tool execution/result.
- `decide_live` — decision made from currently available live evidence; it is not final verification.
- `interrupt_provider` — terminates the provider process after an interrupt decision.
- `live-interrupt.json` — durable record of an interruption decision.
- `context_pages` / `context_digest` — lineage to the exact context selected for the turn.
- `normalize_tool_event` — provider-specific event normalization; it does not execute tools.
- `normalize_usage` / `normalize_cache` — telemetry normalization; neither invents provider facts.
- `streaming_command` — adds provider-native streaming output flags.

These names should remain stable unless the responsibility changes; aliases should not be added merely for stylistic preference.
