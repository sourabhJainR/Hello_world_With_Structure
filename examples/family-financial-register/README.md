# Family Financial Register Reference

A small, offline-first reference model for organizing essential financial continuity information so trusted family members can understand what exists and where to find authoritative records during an emergency or after the account owner is unavailable.

This example uses fake data only. It is not financial, legal, tax, inheritance, custody, or estate advice, and it does not store credentials, private keys, passwords, or recovery codes.

Design goals:
- inventory assets and liabilities;
- identify institution and account reference details without secrets;
- record document location and last-reviewed date;
- identify an appropriate family contact or executor role;
- keep instructions clear and minimal;
- make stale records visible.

`HARNESS_SCENARIOS.md` documents safe control-plane scenarios for this higher-sensitivity example, including complete-job prompting, material-ambiguity handling, security and scope fences, script-first deterministic validation, and proof from deterministic verification.

Run:

```bash
python -m unittest discover -s tests -v
python app.py
```

Security habit: keep real credentials and recovery material outside this register in an appropriate secure mechanism with its own access controls.
