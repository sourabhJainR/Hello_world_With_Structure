---
name: agency-runtime-v11
description: Ragas-inspired, evidence-first codebase retrieval and evaluation for efficient coding.
---

# Agency Runtime v11

## Purpose
Improve coding and codebase information tasks by selecting the smallest useful evidence set, measuring retrieval quality separately from answer quality, and making every unresolved area explicit.

## Flow
`PROFILE -> ADAPT -> INDEX -> RANK PATHS -> SELECT EVIDENCE -> EXECUTE -> VERIFY -> EVALUATE -> REGRESSION -> RELEASE -> BENCHMARK`

## Ragas-derived design
Ragas separates retrieval metrics from response metrics. v11 applies the same discipline to source-code work:

- Context precision: relevant evidence should rank early.
- Context recall: expected evidence should not be silently missed.
- Path hit rate: expected files must be surfaced when known.
- Response relevancy: the answer must address the requested codebase question.
- Faithfulness: answer claims must be supported by selected evidence.
- Answer correctness: compare with an optional reference when one exists.

The implementation is dependency-free. It does not import Ragas and therefore does not add an LLM or network dependency to the portable runtime.

## Efficient retrieval
`portable.agency_codebase_context.CodebaseIndex` creates a deterministic repository map containing file hashes, line counts, symbols and imports. `retrieve()` ranks paths before reading content and selects bounded line windows until the token budget is exhausted.

The context returned to a coding worker includes:
- snapshot digest
- selected paths
- exact line ranges
- evidence text
- estimated token count
- scanned/read file counts
- explicit unknowns and budget omissions

## Unknown policy
Unknowns are first-class data. Examples include no path/symbol match, unreadable files, and relevant files omitted by the context budget. The runtime must never convert an unknown into an inferred implementation detail.

## Host boundary
The host still owns filesystem access, credentials, tool execution, mutation, concurrency and side effects. v11 only indexes and selects read-only evidence before execution.

## Verification
Run:
`python -m py_compile portable/agency_codebase_context.py portable/agency_ragas_eval.py portable/agency_runtime.py portable/ai_coding_agency_bridge.py`
`python -m unittest tests/test_agency_codebase_context.py tests/test_agency_ragas_eval.py tests/test_ai_coding_codebase_context.py -v`
`python -m unittest discover -s tests -p 'test_agency_*.py' -v`
