# AER Capability Contract

This is the single contract for the operational capabilities adopted from the Hermes Agent design review. The implementation is AER-native; existing AER orchestration, sandbox, hooks, context, TaskPlan, provider fabric, session store and learning gates remain authoritative.

## Capability map

| Capability | AER implementation | Authority | Fallback |
|---|---|---|---|
| Toolsets | `portable.hermes_capabilities.CapabilityRegistry` | AER registry | `safe` / `coding` / `research` / `automation` |
| Web + X search | registry + verified adapters | provider evidence | general search |
| Terminal + files | `ProcessManager` + `TerminalBackends` + AER sandbox | sandbox/policy | local sandbox |
| Browser / vision / image generation / TTS | registry/native adapters | provider evidence | unavailable until verified |
| Persistent memory | `MemoryStore` | AER state root | explicit disable only |
| Session recall | `MemoryStore.index_session/search_session` | session + FTS5 | no model call |
| Progressive skills | `SkillRegistry` | skill roots + metadata | no activation when prerequisites fail |
| Todo/planning | `TaskPlan` | AER task contract | single task execution |
| Background work | `ProcessManager` | process receipts | foreground execution |
| Delegation | `DelegationManager` + `TaskPlan` | TaskPlan dependency graph | single-agent execution |
| Scheduling | `CronStore` | AER durable job state | manual run |
| Code execution / clarify | AER runtime capability registry | runtime/security gates | unavailable/fallback |
| MCP | provider/native adapter registry | verified provider evidence | unavailable |
| Provider/model fallback | `ProviderFabric` | discovered capability evidence | AER fallback |
| Completion quality | `OutputQualityGate` | evidence + verification | BLOCKED, never fabricated success |

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

No capability may bypass state, security, approval, verification or learning gates.

## Toolset policy

`safe` is least privilege. `coding` adds terminal/files/skills/delegation/code execution. `research` adds web/X search/browser surfaces. `automation` adds scheduling. `full` means all registered capabilities, not unrestricted authority; every capability remains subject to its own policy.

## Memory policy

Memory is bounded, explicit and deduplicated. Secret/injection/bidi scans run before persistence. Approval staging is available for future-facing mutations. Session recall uses SQLite FTS5 and stores exact session messages without replaying whole transcripts.

Memory never overrides repository rules, task acceptance, verification evidence or the current context lease.

## Skills policy

Skills are progressive-disclosure knowledge, not executable authority. Metadata is inspected before full content; references are loaded on demand. Platform/tool prerequisites can suppress activation. Learned skills are scanned and remain subject to repository verification.

## Delegation and background policy

Delegation consumes `TaskPlan`. Independent tasks may run concurrently. Failed or blocked prerequisites prevent dependents from running. Child results are bounded receipts. Long-running work that must survive process/session boundaries uses scheduled/background mechanisms rather than process-local delegation.

## Terminal policy

Backends are explicit: local, Docker, SSH, Singularity/Apptainer, Modal, Daytona and Vercel Sandbox. External adapters are never simulated. Backend selection never bypasses AER sandbox, permission or approval controls.

## Provider policy

Provider/model selection is evidence-driven. Deterministic fallback may change transport/provider, but never changes task acceptance, security or verification requirements.

## Scheduling policy

Cron stores durable schedule state. Each due job re-enters the same AER lifecycle and must leave evidence and verification receipts.

## Output-quality policy

A polished model response is not completion. Acceptance requires explicit outcome, changed paths, verification and evidence. Missing proof becomes incomplete/blocked state.

## Canonical authority rules

1. `portable/hermes_capabilities.py` is the stable import surface; `portable/hermes_capabilities_core.py` is the sole implementation.
2. `.ai-harness/config.toml` is the runtime configuration source.
3. `portable/adaptive_runtime.py` is the public composition point.
4. `TaskPlan` owns dependency scheduling; no second scheduler is authoritative.
5. `ProviderFabric` owns provider capability/fallback routing; no capability-specific provider table is authoritative elsewhere.
6. `.ai-harness/CONTEXT_POLICY.md` owns context selection; memory/skills are inputs, not competing prompt assemblers.
7. `.ai-harness/ORCHESTRATION_SPEC.md` owns execution state and evidence precedence.
8. `.ai-harness/ARTIFACT_UPGRADE_CONTRACT.json` owns deployment compatibility.
9. The three agent-facing skill entrypoints must remain byte-for-byte identical.

## Non-goals

Do not copy Hermes UI, gateway adapters, provider-specific business logic or third-party service implementations into AER. Optional integrations are adapters behind the same capability contract. The aim is a stronger engineering control plane, not a second chat application.
