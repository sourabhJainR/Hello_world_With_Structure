---
name: code-review
description: Review a change against repository standards and its originating requirements as separate axes.
---

# Code Review

Review the current diff from a fixed point such as a commit, branch, or merge-base. Do not treat a passing test suite as review completion.

## Standards axis

Check repository instructions, coding conventions, ownership, dependency direction, error handling, security, observability, concurrency, and testing. Also look for duplicated logic, primitive domain concepts, shotgun surgery, divergent change, speculative abstractions, message chains, and middle-man delegation. Treat heuristic smells as judgement calls unless the repository explicitly makes them hard rules.

## Requirement axis

Trace the originating request, issue, spec, or acceptance criteria. Report missing behavior, partial behavior, incorrect behavior, and scope creep separately from standards findings.

## Evidence

For each material finding capture file/symbol, impact, and evidence. Re-run focused verification after a corrective change. Preserve the same intent and context evidence digest. Emit the resulting review evidence through the existing provenance ledger and bind it to the verified artifact.

## Review gate

No material unresolved finding may proceed to the next rollout gate. Review is independent of generation: inspect the produced artifact, its data flow, failure paths, security posture, compatibility, and evidence rather than trusting the author's summary.
