# AI Coding Best Practices

This document is the provider-neutral engineering playbook for AI-assisted software work.

## 1. Outcome first

Define the desired behavior, acceptance criteria, constraints, non-goals, and stopping condition before implementation. Do not optimize for producing code; optimize for a verified outcome.

## 2. Inspect before edit

Build the smallest useful understanding of the repository first. Prefer targeted search, repository maps, dependency inspection, tests, and nearby examples over broad file dumps.

## 3. Evidence before assumption

Treat repository evidence, executed commands, tests, logs, and authoritative external sources as evidence. Label assumptions and uncertainty explicitly.

## 4. Smallest safe change

Prefer the smallest change that satisfies the requirement without reducing correctness, security, maintainability, or compatibility.

## 5. DRY, but not prematurely

Remove meaningful duplication when behavior or change ownership is shared. Do not create abstractions merely because two fragments look similar.

## 6. YAGNI

Do not implement speculative features, generalized frameworks, unused configuration, or abstractions for hypothetical future requirements.

## 7. KISS

Prefer the simplest design that meets the current constraints and is easy for another engineer to understand and change.

## 8. Dependency control

Keep volatile or external concerns replaceable at the appropriate boundary. Use dependency injection, dependency inversion, composition, ports, adapters, or the language's equivalent when it materially improves testability or changeability. Do not create interfaces solely to satisfy a rule.

## 9. Cohesion and coupling

Keep responsibilities focused and dependencies explicit. Minimize unnecessary cross-module knowledge and avoid hidden coupling.

## 10. Compatibility by default

Preserve public behavior, data contracts, configuration semantics, and operational expectations unless the task explicitly requires a breaking change.

## 11. Tests prove behavior

Prefer focused tests around acceptance criteria, edge cases, regressions, failure handling, and critical contracts. Do not add tests only to increase line coverage.

## 12. Test after meaningful state changes

Validate after implementation, after corrective fixes, and before declaring completion. Use the smallest relevant check first, then expand validation when risk warrants it.

## 13. Security by default

Treat authentication, authorization, secrets, untrusted input, data exposure, dependency risk, and privileged operations as first-class concerns. For material security work, trigger adversarial review.

## 14. Failure-aware design

Explicitly consider retries, timeouts, partial failure, cancellation, idempotency, concurrency, corruption, resource exhaustion, and degraded dependencies where relevant.

## 15. Observability

For production-impacting changes, preserve or add enough logging, metrics, traces, diagnostics, or actionable errors to understand failures without exposing sensitive data.

## 16. Reversibility

For migrations and high-risk changes, prefer staged rollout, compatibility windows, rollback paths, feature flags, or other reversible mechanisms when appropriate.

## 17. Least privilege

Use the minimum permissions, tools, files, credentials, and external access needed for the task.

## 18. Diff discipline

Review the final diff for unrelated changes, generated noise, dead code, accidental API changes, secrets, debug artifacts, and unnecessary complexity.

## 19. Stop when done

A task is complete when acceptance criteria are satisfied and evidence supports completion. Do not continue refactoring without a measurable reason.

## 20. AI-specific rules

- Use the minimum capable model and reasoning effort that can safely solve the task.
- Escalate model capability when complexity, uncertainty, or risk increases.
- Prefer structured summaries over replaying full transcripts.
- Delegate independent workstreams only when they can be parallelized safely.
- Keep subagent instructions narrow and outputs bounded.
- Use cached or reusable context for stable repository instructions and compact maps when the provider supports it.
- Expose only the tools relevant to the current phase.
- Set explicit success criteria and stopping rules for long-running tasks.
- Verify generated changes with repository-native checks instead of trusting the model's claims.
- When a tool, test, or source is unavailable, say so and continue with the safest grounded alternative.

## 21. Review questions

Before completion, ask:

1. Did we solve the stated problem rather than a nearby problem?
2. Did we change more than necessary?
3. Is any new abstraction justified by multiple concrete uses or a clear boundary?
4. Is the behavior tested at the right level?
5. What can fail in production that the happy path hides?
6. What assumptions remain unverified?
7. Can the change be rolled back or contained if it causes trouble?
8. Are there security, privacy, reliability, performance, or compatibility concerns?
9. Does the final diff contain anything unrelated?
10. Is there a simpler solution?
