# Security Policy

## Reporting a vulnerability

Please do not disclose security-sensitive findings in a public issue.

Use a private security reporting channel associated with the repository owner, or contact the maintainer directly with:

- affected version or commit;
- affected component/path;
- reproducible steps or a minimal proof of concept;
- expected and observed behavior;
- impact assessment;
- any proposed mitigation, if known.

Do not include customer source code, credentials, API keys, private prompts, or other sensitive data in a report.

## Security boundaries

The orchestrator may invoke local AI CLIs and repository tooling. Treat generated commands and provider output as untrusted until execution policy and verification gates allow them.

The system must not silently:

- install third-party software;
- change permissions;
- connect to production;
- merge or deploy changes;
- transmit repository content to an external service;
- promote learned behavior into executable policy.

Optional telemetry and external integrations must be explicitly configured and documented.

## Commercial deployment

For enterprise deployments, keep organization memory, evaluation data, regression history, credentials, and proprietary connector implementations outside the public repository. Use tenant isolation and least-privilege credentials.

## Supply-chain controls

Official releases should be reproducible or auditable from a pinned source commit and should publish release provenance. Third-party dependencies must be disclosed with their licenses and purpose.
