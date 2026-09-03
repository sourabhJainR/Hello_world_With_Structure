# AI Coding Harness Security Model

## Trust boundary

The model is not trusted. Repository content, Jira text, logs, generated code, tool output, external documents, and learned memory are untrusted data. Repository-local policy and the immutable task contract remain authoritative.

## Provider execution

All configured Claude, Codex, and Gemini invocations pass through `security_gate.py` and `provider.py`.

The gate:

- rejects arbitrary provider executables;
- rejects common permission-escalation flags;
- forces plan/read-only mode for analysis-only tasks;
- restricts prompt files to the active run directory;
- forwards only a conservative environment allowlist and provider authentication variables.

This is a policy gate, not an OS sandbox. A production deployment that permits agents to execute arbitrary shell commands should additionally run the provider in an isolated container or VM with short-lived credentials, restricted network access, resource limits, and an explicit filesystem policy.

## High-risk work

High-risk work requires isolated worktrees, independent review, and consensus. The repository must not treat a successful model exit code as proof of correctness.

Durable execution journal failures are fatal to the run because losing the audit trail during a high-impact change is itself a correctness failure.

## Secret handling

Do not put long-lived production credentials into agent-visible environment variables. The current gate removes unrelated credential-like environment variables, but provider API keys are retained because standard CLI authentication may require them. A future enterprise deployment should replace this with a credential broker that gives the provider only short-lived, task-scoped credentials.

## Evidence standard

A claim such as "verified", "confirmed", or "no regression" must be backed by recorded verification evidence. The Engineering State Ledger is the durable contract for intent, evidence, changeset, verification, risks, and outcome.
