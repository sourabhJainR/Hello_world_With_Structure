# Agency Runtime v8 integration

Substantial coding tasks should use `portable.ai_coding_agency_bridge` as the Agency control-plane boundary.

The bridge owns task profiling, deterministic specialist planning, structured evidence, provenance, artifact regression and release decisioning.

The host AI coding orchestrator remains authoritative for provider/tool execution, sandboxing, permissions, concurrency, mutation ordering and external side effects.

A successful task requires all applicable quality hard gates, no blocker/material findings, successful regression checks when a baseline exists, and a final `passed` release decision.
