# Harness Memory

`observations.jsonl` stores run-level evidence. `patterns.jsonl` stores reusable candidate patterns.

Memory is intentionally separate from executable harness code. A pattern is promoted only after repeated observations and an acceptable success rate. `python .ai-harness/run.py groom` consolidates memory.

Do not store secrets, credentials, access tokens, or private data in memory.