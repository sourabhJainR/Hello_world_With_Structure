# Canonical Evidence Spine

`state/engineering-state.schema.json:evidence` remains the sole canonical evidence record contract.

`portable/evidence_contract.py` is a dependency-free validation view over those records. It is not a persistent store and must not become a competing evidence authority.

The executable boundary validates evidence identity, source, claim, confidence, repository snapshot, provenance, duplicate IDs, and reference existence/freshness.

Required lineage:

```text
Repository model snapshot -> evidence claim -> evidence reference -> execution -> verification
```

Reports, architecture views, and learning may consume evidence identifiers, but they cannot promote themselves to evidence authority.
