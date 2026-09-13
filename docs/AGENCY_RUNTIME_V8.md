# Agency Runtime v8 — AI Coding Orchestrator Integration

## Purpose

v8 makes the Agency Runtime the deterministic control plane around substantial AI coding tasks while leaving provider and tool execution with the existing AI coding orchestrator.

## Flow

`profile -> route -> plan -> execute(host) -> evidence -> verify -> regression -> release`

The bridge is `portable.ai_coding_agency_bridge.run_coding_task`.

## Responsibilities

The bridge owns task profiling, specialist assignment, structured evidence capture, provenance, artifact regression comparison, and release decisioning.

The host orchestrator remains responsible for provider calls, terminal/file tools, permissions, sandboxing, concurrency, mutation ordering, credentials, networking, and external side effects.

## Release rule

A high quality score is not sufficient. The run must satisfy hard gates, have no blocker/material findings, pass artifact regression when a baseline is supplied, and end with a `passed` release decision.

## Verification

```bash
python -m py_compile portable/agency_*.py portable/ai_coding_agency_bridge.py
python -m unittest discover -s tests -p 'test_agency_*.py' -v
python -m unittest tests/test_ai_coding_agency_bridge.py -v
```

No external Python runtime dependencies are required by this integration.
