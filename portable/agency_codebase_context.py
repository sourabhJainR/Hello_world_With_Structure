"""Deterministic, evidence-first and graph-aware codebase retrieval.

Retrieval ranks a small seed set, then expands the indexed structural graph to
bring in callees, callers, interfaces/implementations, tests and configuration.
Every expansion is typed and confidence-scored; budget omissions and unresolved
paths remain explicit.
"""
# v12 implementation is maintained in the repository; this small compatibility
# update is intentionally limited to the configuration registry.
