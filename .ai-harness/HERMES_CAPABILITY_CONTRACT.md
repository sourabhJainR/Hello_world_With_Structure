# Unified Agent Capability Contract

This document is the canonical mapping of the useful Hermes Agent capabilities into AER. AER keeps ownership of intent, security, context, evidence, verification, scheduling, and learning.

## Capability surface

The public surfaces are intentionally small:

- `portable.capability_fabric.CapabilityFabric` — capability discovery and safe planning.
- `portable.persistent_memory.PersistentMemory` — bounded intent-scoped memory and recall.
- `portable.automation_scheduler.AutomationScheduler` — durable schedule, claim, retry and run state.
- `portable.output_quality.OutputQualityGate` — objective completion-quality gate.

All four delegate to the single implementation in `portable.agent_capabilities`. There is no second runtime hidden behind these modules.

## Covered capabilities

`web_search`, `x_search`, `terminal`, `browser`, `file`, `vision`, `image_generation`, `tts`, `todo`, `memory`, `session_search`, `cronjob`, `execute_code`, `delegate_task`, `clarify`, `mcp`, `skills`, `background_processes`, and `provider_fallback`.

Provider-native support is selected only when discovered. Optional external adapters are never reported as available without evidence.

## Runtime behavior

```text
INTENT
  -> CONTEXT BROKER
  -> CAPABILITY PLAN
  -> TASK PLAN
  -> IMPACT / MUTATION BOUNDARY
  -> PROVIDER + TOOL ROUTING
  -> EXECUTION / DELEGATION
  -> DURABLE RECEIPTS
  -> VERIFICATION
  -> OUTPUT QUALITY GATE
  -> REVIEW
  -> LEARN (candidate only)
```

### Memory
Memory is bounded, redaction-aware, intent-scoped, deduplicated and approval-aware. Session recall is durable search rather than full transcript replay. Memory never overrides repository instructions or verification evidence.

### Skills
Skills remain progressive-disclosure knowledge. Metadata and prerequisites are inspected before loading full procedures. Skill content is not authority and cannot override repository/security policy.

### Delegation
Delegation reuses the existing `TaskPlan` dependency contract. Independent work may run in parallel; failed/blocked prerequisites prevent dependents from running. Child work returns bounded evidence/receipts for parent verification.

### Background work and scheduling
Long-running work uses durable scheduling/background state. Scheduler claims prevent duplicate execution and retries remain bounded. Scheduled work re-enters the same AER lifecycle rather than receiving a privileged execution path.

### Terminal and sandbox
Terminal execution remains under AER sandbox controls. Alternate backends are adapter points, not a bypass. Local, Docker, SSH, Singularity/Apptainer, Modal, Daytona and Vercel Sandbox are explicit supported backend identifiers; external execution requires verified configuration.

### Provider fallback
Fallback changes provider/transport only. It does not change task acceptance, security, context policy, verification or promotion criteria.

### Output quality
A successful model response is not sufficient. Completion requires acceptance, verification, evidence, clean diff, and clean scope. Missing proof produces blocked/incomplete output.

## Authority and anti-silo rules

1. `portable.agent_capabilities` is the sole implementation module for these new capability semantics.
2. The four public capability modules are facades only.
3. `TaskPlan` remains the only task dependency scheduler.
4. `ProviderFabric` remains the only provider routing authority for provider-native lifecycle capabilities; `CapabilityFabric` is for task-facing capability availability/planning and must not duplicate provider routing rules.
5. `CONTEXT_POLICY.md` remains the authority for context selection.
6. `ORCHESTRATION_SPEC.md` remains the authority for state/evidence precedence.
7. Existing sandbox, verification, learning and artifact contracts remain authoritative.
8. The three agent-facing `ai-coding-orchestrator/SKILL.md` files must remain byte-for-byte identical and under the established size budget.
