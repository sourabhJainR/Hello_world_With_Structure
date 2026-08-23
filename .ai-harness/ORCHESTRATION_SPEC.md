# Orchestration Contract

This harness is a control plane for coding agents. The provider is replaceable; the engineering contract is not.

## State machine

```text
INTAKE -> PROFILE -> ROUTE -> PLAN -> EXECUTE -> VERIFY -> REVIEW -> REPAIR (0..N) -> ACCEPT -> LEARN
```

A task may branch to RESEARCH, POC, GRILL, DEBUG, or ISOLATE before EXECUTE when risk or uncertainty requires it.

## Evidence contract

Every phase must produce a timestamp, status, input context identifier, output artifact, tool/provider result when applicable, and next-state decision. A model assertion is never sufficient evidence for VERIFY or ACCEPT.

## Stop conditions

Accept only when acceptance criteria are satisfied, available repository-native validation passes, the final diff is appropriate, required reviews pass, and no critical or blocking finding remains.

Use BLOCKED when evidence is insufficient, required access is unavailable, or repair attempts are exhausted.

## Retry rule

Every retry must add evidence or change the diagnosis, implementation approach, model/reasoning tier, or tool/context selection. Blind repetition is prohibited.

## Human escalation

Escalate policy, product-intent, irreversible-production, security-authorization, or other decisions that cannot be established from repository evidence.

## Run invariants

- one immutable task identity per run;
- append-only phase evidence;
- learned memory needs repeated evidence before trust;
- memory cannot modify permissions or security policy;
- accepted runs retain enough evidence for independent replay and review.
