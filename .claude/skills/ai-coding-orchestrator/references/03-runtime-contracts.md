# Runtime contracts and chat trigger

Keep these aligned:

- `portable.task_planner.TaskPlan`
- `portable.repo_intelligence.RepositoryMap`
- `portable.impact_analysis`
- `portable.agency_execution_plan`
- `portable.agency_team_orchestrator`
- `portable.agency_adaptive_planning`
- `portable.engineering_design_guard.EngineeringDesignGuard`
- `.ai-harness/runtime/tool_runner.py`
- `.ai-harness/runtime/lsp_server.py`
- `.ai-harness/runtime/feedback_loop.py`
- `.ai-harness/runtime/auto_compaction.py`
- `downgrade=explicit_install_only`
- `ORCHESTRATION_SPEC.md`, `TEN_LOOP_POLICY.md`, `CONTEXT_POLICY.md`, `ARCHITECTURE_POLICY.md`
- `ENGINEERING_DESIGN_POLICY.md`, `EXECUTION_POLICY.md`, `VERIFICATION_POLICY.md`, `REVIEW_POLICY.md`
- `LEARNING_POLICY.md`, `TOKEN_POLICY.md`, `PROVIDER_CONTRACT.md`, `QUALITY_GOVERNANCE.md`

## LLM chat trigger

The plugin exposes `adaptive_runtime.trigger` through MCP for durable `AdaptiveRuntime` work. Inputs: `task`, `project_root`, optional `context`, `priority` (`high|normal|low`), `event_id`, and `max_attempts` (1..16). It returns `trigger_id`, `status`, and `accepted_at` after persistence, dispatches through the shared worker pool, and follows normal verification/evidence/policy/learning. Read status from durable trigger state; never create parallel memory, scheduling, orchestration, or privileged paths.

Treat chat-trigger behavior as a capability adapter into the existing runtime, not as a new scheduling, memory, orchestration, or privileged subsystem. Preserve durable lifecycle state, worker ownership, retry bounds, and existing verification gates.
