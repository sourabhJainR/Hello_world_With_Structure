# Verification Pack

Load for verification, regression, review, recovery or release work.

Verification outranks model confidence. Use the smallest sufficient ladder:
`syntax/static -> focused tests -> integration/system -> regression replay -> security/policy -> final diff review`.

A regression claim requires baseline and post-change evidence. Preserve exact test command, exit code, relevant output digest and environment fingerprint. Distinguish pre-existing failures from introduced failures.

For recovery, record an ordered event chain:
`failure injected/observed -> diagnosis -> strategy change -> retry -> successful verification`.
A successful command without the preceding failure does not prove recovery.

Use independent acceptance oracles where practical. Provider statements are diagnostics, not ground truth.

Final gates: scope, diff hygiene, acceptance, protected behavior, security, verification and rollback readiness. Any failed gate blocks a release-ready claim.
