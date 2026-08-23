# Quality Governance

The harness itself is a production system and must be reviewed like one.

## Continuous quality loop

```text
measure -> detect -> hypothesize -> change -> verify -> compare -> promote or revert
```

Review the harness across:

- routing accuracy
- verification escape rate
- repair success rate
- unnecessary capability activation
- context/tool waste
- provider failure rate
- reviewer false-positive/false-negative patterns
- memory promotion quality
- architecture/naming drift
- security and permission drift

## Golden invariants

1. No unverified success.
2. No hidden third-party dependency.
3. No silent security-policy change.
4. No blind retry.
5. No parallel conflicting mutation.
6. No unnecessary context expansion.
7. No invented repository convention.
8. No placement decision without repository evidence when new files are added.
9. No permanent learning from one observation.
10. No external irreversible action without explicit policy approval.

## Entropy control

Periodically scan for duplicated guidance, stale rules, unused capabilities, obsolete provider configuration, dead scripts, weak tests, and contradictory instructions.

Prefer small corrective changes over periodic rewrites.

## Promotion rule

A harness improvement is promoted only when its value is demonstrated through regression tests, representative evaluation cases, or operational evidence.
