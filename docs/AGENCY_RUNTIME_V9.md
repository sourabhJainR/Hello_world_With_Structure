# Agency Runtime v9 — Conflict-Aware Multi-Specialist Planning

v9 extends the v8 AI coding bridge with deterministic scheduling for multiple specialists.

## Resource contract
Each specialist work unit declares:

`ROLE | MUTATION_MODE | READ_PATHS | WRITE_PATHS | DEPENDENCIES | PRIORITY`

Read-only work may share a wave. Any mutation is serialized with other mutation work and with any specialist that reads or writes an overlapping resource.

## Dependency handling
Dependencies are resolved before scheduling. Unknown dependencies and dependency cycles block the affected plan rather than being silently ignored.

## Determinism
The plan is dependency-first and stable for the same inputs. The resulting wave structure and conflicts have a deterministic digest which is recorded by the v8 bridge in provenance.

## Host boundary
The planner does not run commands, acquire credentials, grant permissions, or modify files. The AI coding orchestrator remains the host execution authority.

## Verification
Use:

```bash
python -m py_compile portable/agency_*.py scripts/sync_agency_agents.py scripts/check_agency_agents.py
python -m unittest discover -s tests -p 'test_agency_*.py' -v
python -m unittest tests/test_ai_coding_agency_bridge.py -v
python -m unittest tests/test_agency_execution_plan.py tests/test_agency_multi_specialist.py -v
```

The tests use the Python standard library only.
