# AER Capability Contract

This is the single contract for the operational capabilities added from the Hermes Agent design review. The implementation is AER-native: the existing orchestrator, sandbox, hooks, context policy, task planner, provider fabric, session store and learning gates remain authoritative.

## Capability map

| Capability | AER implementation | Authority | Fallback |
|---|---|---|---|
| Toolsets | `portable.hermes_capabilities.CapabilityRegistry` | AER registry | `safe` / `coding` / `research` / `automation` presets |
| Persistent memory | `MemoryStore` | AER state root | disabled only by explicit config |
| Session recall | `MemoryStore.index_session/search_session` | current session + FTS5 | no model call required |
| Progressive skills | `SkillRegistry` | skill roots + metadata | no activation when prerequisites fail |
| Background work | `ProcessManager` | process receipts | synchronous execution |
| Delegation | `DelegationManager` + `TaskPlan` | `TaskPlan` dependency graph | single-agent execution |
| Scheduling | `CronStore` | AER durable job state | manual run |
| Terminal backends | `TerminalBackends` | configured backend + sandbox | local AER sandbox |
| Provider fallback | `ProviderFabric` | discovered provider evidence | AER fallback |
| Completion quality | `OutputQualityGate` | verification/evidence | BLOCKED, never fabricated success |
| MCP/browser/vision/media | registry/adapters | provider/native evidence | unavailable until verified adapter exists |

## Runtime flow

```text
INTENT
  -> CONTEXT BROKER
  -> CAPABILITY DISCOVERY
  -> TASK PLAN
  -> IMPACT / MUTATION BOUNDARY
  -> PROVIDER + TOOLSET ROUTING
  -> GRAPH / DELEGATION
  -> SANDBOX / TERMINAL
  -> OBSERVE + DURABLE RECEIPTS
  -> VERIFY
  -> QUALITY GATE
  -> REVIEW
  -> LEARN (candidate only)
```

No capability may bypass the state machine, security gate, approval gate, verification gate or learning promotion rules.

## Toolset policy

`safe` is the default least-privilege read-oriented set. `coding` adds terminal, files, skills and delegation. `research` adds web/browser capability. `automation` adds scheduler support. `full` does not mean unrestricted; each capability still passes its own safety and availability checks.

## Memory policy

Memory is compact and explicit. Future-facing memory is bounded by character capacity, rejects duplicates, rejects credential/injection patterns, and supports staged approval. Session recall stores exact messages in SQLite FTS5 and does not spend an LLM call to search history.

Memory is not a replacement for repository instructions, task acceptance, verification evidence or the current context lease.

## Skills policy

Skills are progressive-disclosure knowledge, not executable authority. Discovery returns metadata; `view` loads full content or a reference only when needed. Platform/tool prerequisites can suppress activation. Learned skills must follow the same security scan and repository verification rules as manually authored skills.

## Delegation policy

Delegation is dependency-aware. The parent creates a `TaskPlan`; independent tasks may run concurrently, but dependent tasks cannot begin until prerequisites pass. Child work returns bounded receipts rather than flooding the parent context. Shared mutable resources remain governed by the existing impact-analysis and serialized-mutation rules.

## Background process policy

Long-running processes expose stable handles plus completion receipts. Receipts retain bounded redacted output and expire. A process result may be read by the owning session; absence of a receipt is not evidence that the process succeeded.

## Terminal policy

Backends are selected explicitly: local, Docker, SSH, Singularity/Apptainer, Modal, Daytona or Vercel Sandbox. An external backend is never simulated as available. The backend selection does not bypass AER's sandbox, permission or approval controls.

## Provider policy

Provider selection is evidence-driven. The provider fabric can rank discovered providers and return a deterministic fallback chain. Fallback changes the transport/provider, not the engineering contract, task acceptance or verification requirements.

## Scheduling policy

Cron stores durable schedule state but does not acquire hidden authority. Scheduled runs enter the same AER state machine as interactive work and must leave evidence and verification receipts.

## Output-quality policy

A successful-looking model response is not completion. A task is accepted only with explicit outcome, changed-path, verification and evidence fields. Missing proof produces `BLOCKED`/failure evidence instead of a polished but unsupported answer.

## Compatibility rules

1. `portable/hermes_capabilities.py` is the implementation surface.
2. `.ai-harness/config.toml` is the runtime configuration source.
3. `portable/AdaptiveRuntime` is the public composition point.
4. `TaskPlan` owns dependency scheduling; no second scheduler is allowed.
5. `ProviderFabric` owns provider capability/fallback routing; no capability-specific provider tables are authoritative elsewhere.
6. `.ai-harness/CONTEXT_POLICY.md` owns context selection; skills and memory are inputs to the broker, not competing prompt assemblers.
7. `.ai-harness/ORCHESTRATION_SPEC.md` owns execution state and evidence precedence.
8. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` owns deployment compatibility.

## Non-goals

The project does not copy Hermes' UI, gateway platform adapters, third-party service implementations or provider-specific business logic. Those remain optional adapters behind the capability contract. The goal is a stronger engineering control plane, not a second chat application.
