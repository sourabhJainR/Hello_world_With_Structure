# Agency Runtime v8 — AI Coding Orchestrator Integration

The Agency Runtime is the deterministic control plane around substantial AI coding tasks. The host orchestrator remains responsible for provider/tool execution, permissions, sandboxing, concurrency, mutation ordering, credentials, networking, and external side effects.

Flow: `profile -> route -> plan -> execute(host) -> evidence -> verify -> regression -> release`

The bridge is `portable.ai_coding_agency_bridge.run_coding_task`.

A task is ready only when quality hard gates pass, blocker/material findings are absent, artifact regression passes when a baseline is supplied, provenance verifies, and the release policy returns `passed`.

Verification commands:

```bash
python -m py_compile portable/agency_*.py portable/ai_coding_agency_bridge.py
python -m unittest discover -s tests -p 'test_agency_*.py' -v
```
