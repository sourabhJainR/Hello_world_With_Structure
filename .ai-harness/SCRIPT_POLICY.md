# Deterministic Script-First Policy

Repeatable mechanical work should be implemented once as a deterministic script rather than repeatedly delegated to a model.

## Preferred candidates

- formatting, linting and validation
- repository inventories and metadata extraction
- deterministic code generation from declared schemas
- conversion and normalization
- fixture preparation and test-data transforms
- policy and configuration checks

## Rules

1. Scripts must be bounded, auditable and safe by default.
2. Scripts must not bypass scope, security, approval, verification or staged-change controls.
3. A script recommendation is evidence for routing, not permission to execute an unsafe command.
4. Repeated AI work should be replaced by a script when the task is deterministic and the behavior is stable.
5. Script executions are recorded in the run journal with inputs, output digest, exit status and duration.
6. AI remains responsible for judgment, ambiguity, architecture and acceptance decisions.
