# Agency Runtime v7

The v7 runtime adds two deterministic controls.

## Provenance

`portable/agency_provenance.py` implements an append-only JSONL ledger. Each record contains a sequence number, run ID, event, detail, artifact IDs, a parent hash, and a record hash. The chain can be verified and reloaded from disk; altered or structurally invalid records are rejected.

`ExecutionResult.provenance()` bridges the existing runtime trace into this persistent ledger.

## Artifact regression

`portable/agency_artifact_regression.py` fingerprints files with SHA-256 plus size and compares a baseline with a current run. Unexpected additions, removals, and changes produce deterministic regression findings. Explicitly allowed generated paths can be excluded.

`portable/agency_release.py` now fails release when the regression gate reports `failed`, even when the quality score is otherwise high.

## Verification commands

```bash
python -m py_compile portable/agency_*.py scripts/sync_agency_agents.py scripts/check_agency_agents.py
python -m unittest discover -s tests -p 'test_agency_*.py' -v
```

The v7 modules use only the Python standard library.
